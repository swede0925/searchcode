#!/usr/bin/env python
# -*- coding:utf-8 -*-
import urllib
from hashlib import sha1
import json
import urllib2
from hmac import new as hmac
import gitlab
import multiprocessing

def expand_url(url, params={}):
    """
    :param url:
    :param params:
    :return:
    """
    _url = url
    if params:
        _url += '?'
    paramFormat = '{}={}&'

    for key, value in params.items():
        if isinstance(value, list):
            for value2 in value:
                _url += paramFormat.format(key, urllib.quote_plus(str(value2)))
        else:
            _url += paramFormat.format(key, urllib.quote_plus(str(value)))

    return _url

class ClientError(Exception):
    pass

class ServerError(Exception):
    pass

class AuthError(ClientError):
    pass

class ValidationError(ClientError):
    pass

class SearchCodeClient(object):
    # Default host is local
    DEFAULT_HOST = 'http://localhost'
    DEFAULT_PORT = 7000

    RULES_REPO_LIST_ENDPOINT = '/api/repo/list/'
    RULES_REPO_ADD_ENDPOINT = '/api/repo/add/'
    RULES_REPO_DELETE_ENDPOINT = '/api/repo/delete/'
    RULES_REPO_INDEX_ENDPOINT = '/api/repo/index/'
    RULES_REPO_REINDEX_ENDPOINT = '/api/repo/reindex/'

    def __init__(self, searchcode_url=None, public_key=None, private_key=None):
        self._searchcode_url = searchcode_url or '{}:{}'.format(self.DEFAULT_HOST,self.DEFAULT_PORT)
        self._puplic_key = public_key
        self._private_key = private_key
        self._repository_data = None

    def poll(self):
        self._repository_data = self.repo_list()

    def repository_names(self):
        """
        获取所有项目名字
        :return:
        """
        self.poll()
        return [item['name'] for item in self._repository_data]

    def __len__(self):
        return len(self.repository_names())

    def __contains__(self, repository_name):
        return repository_name in self.repository_names()

    def _get_url(self, endpoint):
        """
        Return the complete url including host and port for a given endpoint.

        :param endpoint: service endpoint as str
        :return: complete url (including host and port) as str
        """
        return '{}{}'.format(self._searchcode_url, endpoint)

    def _make_call(self, endpoint, **data):
        """
        :param endpoint: relative url to make the call
        :param data: queryset or body
        :return: response
        """

        base_url = self._get_url(endpoint)
        url = expand_url(base_url, params=data or {})

        res = urllib2.urlopen(urllib2.Request(url))

        # Analyse response status and return or raise exception
        # Note: redirects are followed automatically by requests
        if res.code < 300:
            # OK, return http response
            return json.loads(res.read())

        elif res.code == 400:
            # Validation error
            msg = ', '.join(e['msg'] for e in res.json()['errors'])
            raise ValidationError(msg)

        elif res.code in (401, 403):
            # Auth error
            raise AuthError(res.reason)

        elif res.code < 500:
            # Other 4xx, generic client error
            raise ClientError(res.reason)

        else:
            # 5xx is server error
            raise ServerError(res.reason)

    def repo_list(self):
        """
        搜索存在的代码仓库
        :return:
        """
        params = {
            'pub': self._puplic_key
        }

        message = "pub=%s" % (urllib.quote_plus(self._puplic_key))

        sig = hmac(self._private_key, message, sha1).hexdigest()

        params['sig'] = sig

        resp = self._make_call( self.RULES_REPO_LIST_ENDPOINT, **params)

        return resp['repoResultList']

    def repo_add(self, reponame, repourl, repobranch,
                 repotype='git', repousername='', repopassword='', reposource='', source = None, sourceuser = None, sourceproject = None):
        """
        添加代码仓库
        :param reponame:
        :param repourl:
        :param repotype:
        :param repousername:
        :param repopassword:
        :param reposource:
        :param repobranch:
        :param source:
        :param sourceuser:
        :param sourceproject:
        :return:
        """
        params = {
            'pub': self._puplic_key,
            'reponame': reponame,
            'repourl': repourl,
            'repotype': repotype,
            'repousername': repousername,
            'repopassword': repopassword,
            'reposource': reposource,
            'repobranch': repobranch
        }

        message = "pub=%s&reponame=%s&repourl=%s&repotype=%s&repousername=%s&repopassword=%s&reposource=%s&repobranch=%s" % (
            urllib.quote_plus(self._puplic_key),
            urllib.quote_plus(reponame),
            urllib.quote_plus(repourl),
            urllib.quote_plus(repotype),
            urllib.quote_plus(repousername),
            urllib.quote_plus(repopassword),
            urllib.quote_plus(reposource),
            urllib.quote_plus(repobranch)
        )

        if not source is None and not sourceuser is None and not sourceproject is None:
            params['source'] = source
            params['sourceuser'] = sourceuser
            params['sourceproject'] = sourceproject

            message += "&source=%s&sourceuser=%s&sourceproject=%s" % (
                urllib.quote_plus(source),
                urllib.quote_plus(sourceuser),
                urllib.quote_plus(sourceproject)
            )

        sig = hmac(self._private_key, message, sha1).hexdigest()
        params['sig'] = sig

        resp = self._make_call(self.RULES_REPO_ADD_ENDPOINT, **params)
        return resp

    def repo_delete(self, reponame):
        """
        删除代码仓库
        :param reponame:
        :return:
        """
        params = {
            'pub': self._puplic_key,
            'reponame': reponame
        }

        message = "pub=%s&reponame=%s" % (
            urllib.quote_plus(self._puplic_key),
            urllib.quote_plus(reponame),
        )

        sig = hmac(self._private_key, message, sha1).hexdigest()
        params['sig'] = sig

        resp = self._make_call(self.RULES_REPO_DELETE_ENDPOINT, **params)
        return resp

    def repo_index(self, repoUrl):
        """
        检索代码
        :param repoUrl:
        :return:
        """
        params = {
            'repoUrl': repoUrl
        }
        resp = self._make_call(self.RULES_REPO_INDEX_ENDPOINT, **params)
        return resp

    def repo_reindex(self):
        """
        重新检索代码
        :return:
        """
        params = {
            'pub': self._puplic_key
        }
        message = "pub=%s" % (urllib.quote_plus(self._puplic_key))

        sig = hmac(self._private_key, message, sha1).hexdigest()
        params['sig'] = sig

        resp = self._make_call(self.RULES_REPO_REINDEX_ENDPOINT, **params)
        return resp

def generate_gitlab_projects_info(gitlab_server, repository_names, queue):
    """
    生成gitlab项目信息
    :param gitlab_server:
    :param queue:
    :return:
    """
    groups = gitlab_server.groups.list(all=True)
    all_groups = [item.name for item in groups]

    all_projects = gitlab_server.projects.list(all=True, as_list=False)

    for item in all_projects:
        reponame = item.path_with_namespace
        repourl = 'git@git.weidai.work:' + reponame + ".git"
        default_branch = item.default_branch

        group = reponame.split('/')[0]
        if default_branch and reponame not in repository_names and group in all_groups and group != 'scm' and group != 'ops' and item.jobs_enabled:
            queue.put((reponame, repourl, default_branch))
            print(u'获取gitlab项目信息: {}, {}, {}'.format(reponame, repourl, default_branch))
    queue.join()

def generate_searchode_repositories(searchcode_server, queue):
    """
    生成searchcode代码仓库
    :param queue:
    :return:
    """
    while True:
        reponame, repourl, default_branch = queue.get()
        try:
            res = searchcode_server.repo_add(reponame, repourl, default_branch)
            index_res = searchcode_server.repo_index(repourl)
            print('{} {}, {}'.format(reponame, res['message'], index_res['message']))
        except Exception as err:
            print(err)
            print('Add Repository {} Failed'.format(reponame))
        queue.task_done()

if __name__ == "__main__":
    # searchcode信息
    searchcode_url = '****'
    public_key = '****'
    private_key = '****'

    # 连接searchcode服务器
    searchcode_client = SearchCodeClient(searchcode_url, public_key, private_key)
    repository_names = searchcode_client.repository_names()

    index_error_repositories = [r['name'] for r in searchcode_client.repo_list() if r['data']['indexError'] != '']
    for er in index_error_repositories:
        try:
            del_res = searchcode_client.repo_delete(er)
            print(er, del_res['message'])
        except Exception as err:
            print(err)
            print('Delete Repository {} Failed'.format(er))

    gitlab_config = {
        'gitlab_url': 'http://git.*.work',
        'email': "****",
        'password': "****"
    }
    #连接gitlab服务器
    gl = gitlab.Gitlab(gitlab_config['gitlab_url'], email=gitlab_config['email'], password=gitlab_config['password'])
    gl.auth()

    q = multiprocessing.JoinableQueue()

    p = multiprocessing.Process(target=generate_gitlab_projects_info, args=(gl, repository_names, q, ))

    c = multiprocessing.Process(target=generate_searchode_repositories, args=(searchcode_client, q, ))
    c.daemon = True

    p.start()
    c.start()

    p.join()

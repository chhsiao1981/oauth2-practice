#!/usr/bin/env python
# -*- coding: utf-8 -*-
from app.constants import S_OK, S_ERR

import gevent.monkey; gevent.monkey.patch_all()
from bottle import Bottle, request, response, route, run, post, get, static_file, redirect, HTTPError, view, template

import random
import math
import base64
import time
import ujson as json
import sys
import argparse
import urllib
from requests_oauthlib import OAuth2Session
from beaker.middleware import SessionMiddleware

from app import cfg
from app import util
from app import util_user
from app.gevent_server import GeventServer

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 1200,
    'session.data_dir': '/data/session',
    'session.auto': True
}

app = Bottle()

@app.route('/')
def r_index():
    return _process_result({"success": True, "msg": "this is home"})


@app.get('/with_check')
def p_with_check():
    (error_code, user_info) = util_user.is_valid_user(request)
    cfg.logger.warning('after is_valid_user: error_code: %s user_info: %s', error_code, user_info)
    if error_code != S_OK:
        _redirect_login()
        return

    return _process_result({"success": True, "user_info": user_info})


@app.get('/without_check')
def g_without_check():
    (error_code, user_info) = util_user.is_valid_user_without_check()

    return _process_result({"success": True, "error_code": error_code, "user_info": user_info})


@app.put('/<the_id>')
def put_id(the_id):
    return ''


@app.delete('/<the_id>')
def d_id(the_id):
    return ''


@app.get('/register')
def register():
    (session_struct, session_struct2) = util_user.process_session(request)
    cfg.logger.debug('session_struct: %s session_struct2: %s', session_struct, session_struct2)

    headers = dict(request.headers)
    cookies = dict(request.cookies)
    params = _process_params()
    state = params.get('state', '')

    cfg.logger.debug('params: %s headers: %s session_struct: %s cookies: %s state: %s', params, headers, session_struct, cookies, state)

    client_id = cfg.config.get('oauth2_client_id', '')
    redirect_uri = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/register'
    scope = [
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    # fetch token
    token_url = "https://accounts.google.com/o/oauth2/token"
    #the_path = params.get('url', '')
    qs = urllib.urlencode(params)

    redirect_url = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/register?' + qs

    client_secret = cfg.config.get('oauth2_client_secret', '')

    cfg.logger.debug('redirect_url: %s', redirect_url)

    token = google.fetch_token(token_url, client_secret=client_secret, 
                           authorization_response=redirect_url)

    cfg.logger.debug('after fetch_token: token: (%s, %s)', token, token.__class__.__name__)

    # get user info
    r = google.get('https://www.googleapis.com/oauth2/v1/userinfo')

    the_struct = util.json_loads(r.content)

    user_id = 'google_' + str(the_struct['id'])

    # save
    util_user.save_user(user_id, session_struct.get('key', ''), session_struct2.get('key', ''), {"google_id": the_struct['id'], 'name': the_struct['name'], 'given_name': the_struct['given_name'], 'family_name': the_struct['family_name'], 'token': token})

    util_user.save_session_user_map(session_struct, user_id)
    util_user.save_session_user_map(session_struct2, user_id)

    cfg.logger.debug('user_info: r.content: (%s, %s) the_struct: (%s, %s)', r.content, r.content.__class__.__name__, the_struct, the_struct.__class__.__name__)

    # return
    login_info = util.db_find_one('login_info', {"state": state})

    qs = login_info.get('url', '')

    redirect_url = 'http://' + cfg.config.get('sitename', 'localhost') + qs

    cfg.logger.warning('to redirect: redirect_url: %s', redirect_url)

    redirect(redirect_url)


@app.get('/logout')
def logout():
    (session_struct, session_struct2) = util_user.process_session(request)
    util_user.remove_session(session_struct)
    util_user.remove_session(session_struct2)

    the_url = 'http://' + cfg.config.get('sitename', 'localhost')
    redirect(the_url)


@app.get('/login')
def login():
    (session_struct, session_struct2) = util_user.process_session(request)
    cfg.logger.debug('session_struct: %s session_struct2: %s', session_struct, session_struct2)

    params = _process_params()
    the_path = params.get('url', '')

    the_timestamp = util.get_timestamp()

    cfg.logger.debug('params: %s the_path: %s', params, the_path)

    client_secret = cfg.config.get('oauth2_client_secret', '')

    authorization_base_url = "https://accounts.google.com/o/oauth2/auth"

    client_id = cfg.config.get('oauth2_client_id', '')
    redirect_uri = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/register'
    scope = [
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    authorization_url, state = google.authorization_url(authorization_base_url,
                                                        # offline for refresh token
                                                        # force to always make user click authorize
                                                        approval_prompt="auto")

    util.db_insert('login_info', {"state": state, "the_timestamp": the_timestamp, "params": params, "url": the_path})

    cfg.logger.debug('after authorization_url: authorization_url: %s state: %s', authorization_url, state)

    redirect(authorization_url)


def _redirect_login():
    the_url = request.path + '?' + request.query_string
    qs_dict = {"url": the_url}
    qs = urllib.urlencode(qs_dict)
    cfg.logger.warning('the_url: %s qs: %s', the_url, qs)
    redirect_url = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/login?' + qs
    redirect(redirect_url)


def _process_params():
    return dict(request.params)


def _process_result(the_result):
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods', '*')
    #cfg.logger.debug('the_obj: %s', the_obj)
    response.content_type = 'application/json'
    return util.json_dumps(the_result)


def parse_args():
    ''' '''
    parser = argparse.ArgumentParser(description='oauth2_backend')
    parser.add_argument('-i', '--ini', type=str, required=True, help="ini filename")
    parser.add_argument('-p', '--port', type=str, required=True, help="port")

    args = parser.parse_args()

    return (S_OK, args)


if __name__ == '__main__':
    (error_code, args) = parse_args()

    cfg.init({"port": args.port, "ini_filename": args.ini})

    app = SessionMiddleware(app, session_opts)

    run(app, host='0.0.0.0', port=cfg.config.get('port'), server=GeventServer)

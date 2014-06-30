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
    (session_key, session_key2) = _process_session()
    cfg.logger.debug('session_key: %s session_key2: %s', session_key, session_key2)

    headers = dict(request.headers)
    cookies = dict(request.cookies)
    params = _process_params()
    login_key = params.get('key', '')

    cfg.logger.debug('params: %s headers: %s session_key: %s cookies: %s login_key: %s', params, headers, session_key, cookies, login_key)

    client_id = cfg.config.get('oauth2_client_id', '')
    redirect_uri = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/register'
    scope = [
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    token_url = "https://accounts.google.com/o/oauth2/token"
    #the_path = params.get('url', '')
    #qs = urllib.urlencode(params)

    redirect_url = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/register'

    client_secret = cfg.config.get('oauth2_client_secret', '')

    cfg.logger.debug('redirect_url: %s', redirect_url)

    token = google.fetch_token(token_url, client_secret=client_secret, 
                           authorization_response=redirect_url)

    cfg.logger.debug('after fetch_token: token: (%s, %s)', token, token.__class__.__name__)

    r = google.get('https://www.googleapis.com/oauth2/v1/userinfo')

    the_struct = util.json_loads(r.content)

    user_id = 'google_' + str(the_struct['id'])
    util.db_update('user_info', {"user_id": user_id}, {"google_id": the_struct['id'], 'name': the_struct['name'], 'given_name': the_struct['given_name'], 'family_name': the_struct['family_name'], 'session_key': session_key, 'session_key2': session_key2, 'token': token})

    util.db_update('session_user_map', {"session_key": session_key}, {"user_id": user_id})
    util.db_update('session_user_map', {"session_key": session_key2}, {"user_id": user_id})

    cfg.logger.debug('user_info: r.content: (%s, %s) the_struct: (%s, %s)', r.content, r.content.__class__.__name__, the_struct, the_struct.__class__.__name__)

    login_info = util.db_find_one('login_info', {"login_key": login_key})

    qs = login_info.get('url', '')

    redirect_url = 'http://' + cfg.config.get('sitename', 'localhost') + qs

    cfg.logger.warning('to redirect: redirect_url: %s', redirect_url)

    redirect(redirect_url)


@app.get('/logout')
def logout():
    (session_key, session_key2) = _process_session()
    _remove_all(session_key)
    _remove_all(session_key2)

    the_url = 'http://' + cfg.config.get('sitename', 'localhost')
    redirect(the_url)


@app.get('/login')
def login():
    (session_key, session_key2) = _process_session()
    cfg.logger.debug('session_key: %s session_key2: %s', session_key, session_key2)

    params = _process_params()
    the_path = params.get('url', '')

    the_timestamp = util.get_timestamp()

    login_key = str(the_timestamp) + '_' + util.gen_random_string()

    cfg.logger.debug('params: %s the_path: %s', params, the_path)

    util.db_insert('login_info', {"login_key": login_key, "the_timestamp": the_timestamp, "params": params, "url": the_path})

    client_secret = cfg.config.get('oauth2_client_secret', '')

    authorization_base_url = "https://accounts.google.com/o/oauth2/auth"

    client_id = cfg.config.get('oauth2_client_id', '')
    redirect_uri = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/register?key=' + login_key
    scope = [
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    authorization_url, state = google.authorization_url(authorization_base_url,
                                                        # offline for refresh token
                                                        # force to always make user click authorize
                                                        access_type="offline", approval_prompt="auto")

    cfg.logger.debug('after authorization_url: authorization_url: %s state: %s', authorization_url, state)

    redirect(authorization_url)


def _redirect_login():
    the_url = request.path + '?' + request.query_string
    qs_dict = {"url": the_url}
    qs = urllib.urlencode(qs_dict)
    cfg.logger.warning('the_url: %s qs: %s', the_url, qs)
    redirect_url = 'https://' + cfg.config.get('sitename_ssl', 'localhost') + '/login?' + qs
    redirect(redirect_url)


def _process_session():
    session = request.environ['beaker.session']
    session_key = ''
    session_key2 = ''
    the_timestamp = util.get_timestamp()
    if not session.has_key('value'):
        session_key = util.gen_random_string() + '_' + str(the_timestamp)
        session_key2 = util.gen_random_string() + '_' + str(the_timestamp + 300)
        session['value'] = session_key
        session['value2'] = session_key2
        session.save()
    else:
        session_key = session['value']
        session_key2 = session['value2']
        (session_id, session_timestamp) = session_key.split('_')
        (session_id2, session_timestamp2) = session_key.split('_')
        if the_timestamp - util._int(session_timestamp) >= 300:
            new_timestamp = max(the_timestamp, util._int(session_timestamp2) + 300)
            session_key3 = util.gen_random_string() + '_' + str(new_timestamp)
            session['value'] = session_key2
            session['value2'] = session_key3
            session.save()

    return (session_key, session_key2)


def _process_params():
    return dict(request.params)


def _process_result(the_result):
    response.set_header('Access-Control-Allow-Origin', '*')
    response.set_header('Access-Control-Allow-Methods', '*')
    #cfg.logger.debug('the_obj: %s', the_obj)
    response.content_type = 'application/json'
    return util.json_dumps(the_result)


def _remove_all(session_key):
    util.db_update('user_info', {'session_key': session_key}, {'session_key': ''}, multi=True)
    util.db_update('user_info', {'session_key2': session_key}, {'session_key2': ''}, multi=True)
    util.db_remove('session_user_map', {"session_key": session_key})


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

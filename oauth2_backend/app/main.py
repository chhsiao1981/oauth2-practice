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

from app.constants import *
from app import cfg
from app import util
from app import util_user
from app import util_login
from app.gevent_server import GeventServer

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
    (error_code, user_info) = util_user.is_valid_user_without_check(request)

    return _process_result({"success": True, "error_code": error_code, "user_info": user_info})


@app.put('/<the_id>')
def put_id(the_id):
    return ''


@app.delete('/<the_id>')
def d_id(the_id):
    return ''


@app.get('/register_google')
def register():
    params = _process_params()
    util_login.register_google(request, params)
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
    login_google()
    pass


@app.get('/login_google')
def login_google():
    params = _process_params()
    util_login.login_google(request, params)


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


def _main():
    global app

    (error_code, args) = parse_args()

    cfg.init({"port": args.port, "ini_filename": args.ini})

    expire_unix_timestamp_session = cfg.config.get('expire_unix_timestamp_session', EXPIRE_UNIX_TIMESTAMP_SESSION)

    session_opts = {
        'session.type': 'file',
        'session.timeout': expire_unix_timestamp_session,
        'session.data_dir': '/data/session',
        'session.auto': True
    }

    app = SessionMiddleware(app, session_opts)

    run(app, host='0.0.0.0', port=cfg.config.get('port'), server=GeventServer)


if __name__ == '__main__':
    _main()

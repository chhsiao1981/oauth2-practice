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
from app.gevent_server import GeventServer

session_opts = {
    'session.type': 'file',
    'session.cookie_expires': 300,
    'session.data_dir': '/data/session',
    'session.auto': True
}

app = Bottle()

@app.route('/')
def r_index():
    return ''

@app.post('/<the_id>')
def p_id(the_id):
    return ''

@app.get('/<the_id>')
def g_id(the_id):
    return ''

@app.put('/<the_id>')
def put_id(the_id):
    return ''

@app.delete('/<the_id>')
def d_id(the_id):
    return ''


@app.get('/register')
def register():
    headers = dict(request.headers)
    cookies = dict(request.cookies)
    params = _process_params()
    cfg.logger.debug('params: %s headers: %s cookies: %s', params, headers, cookies)

    client_id = cfg.config.get('oauth2_client_id', '')
    redirect_uri = 'https://' + cfg.config.get('sitename', 'localhost') + '/register'
    scope = [
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    token_url = "https://accounts.google.com/o/oauth2/token"
    the_path = params.get('url', '')
    qs = urllib.urlencode(params)

    redirect_url = 'https://' + cfg.config.get('sitename', 'localhost') + '/register?' + qs

    client_secret = cfg.config.get('oauth2_client_secret', '')

    cfg.logger.debug('redirect_url: %s', redirect_url)

    google.fetch_token(token_url, client_secret=client_secret, 
                       authorization_response=redirect_url)

    cfg.logger.debug('after fetch_token')

    r = google.get('https://www.googleapis.com/oauth2/v1/userinfo')

    the_struct = util.json_loads(r.content)

    cfg.logger.debug('user_info: r: (%s, %s) the_struct: (%s, %s)', r.content, r.content.__class__.__name__, the_struct, the_struct.__class__.__name__)

    return {"success": True}


@app.get('/login')
def login():
    params = _process_params()
    the_path = params.get('url', '')

    cfg.logger.debug('params: %s the_path: %s', params, the_path)

    client_secret = cfg.config.get('oauth2_client_secret', '')

    authorization_base_url = "https://accounts.google.com/o/oauth2/auth"

    client_id = cfg.config.get('oauth2_client_id', '')
    redirect_uri = 'https://' + cfg.config.get('sitename', 'localhost') + '/register'
    scope = [
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    google = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    authorization_url, state = google.authorization_url(authorization_base_url,
                                                        # offline for refresh token
                                                        # force to always make user click authorize
                                                        access_type="offline", approval_prompt="force")

    cfg.logger.debug('after authorization_url: authorization_url: %s state: %s', authorization_url, state)

    redirect(authorization_url)


def _process_params():
    return dict(request.params)


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

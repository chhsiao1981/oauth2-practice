# -*- coding: utf-8 -*-

from app.constants import S_OK, S_ERR
import random
import math
import base64
import time
import ujson as json
from requests_oauthlib import OAuth2Session
from bottle import redirect
import urllib
from requests_oauthlib.compliance_fixes import facebook_compliance_fix

from app.constants import *
from app import cfg
from app import util
from app import util_user


def login_google(request, params):
    client_id = cfg.config.get('google_oauth2_client_id', '')

    scope = cfg.config.get('google_oauth2_scope', ["https://www.googleapis.com/auth/userinfo.profile"])
    register_uri = cfg.config.get('sitename_ssl', 'localhost') + cfg.config.get('google_oauth2_register', '/register_google')
    authorization_base_url = cfg.config.get('google_oauth2_auth_url', "https://accounts.google.com/o/oauth2/auth")

    _login(client_id, scope, register_uri, authorization_base_url, request, params)


def register_google(request, params):
    client_id = cfg.config.get('google_oauth2_client_id', '')
    client_secret = cfg.config.get('google_oauth2_client_secret', '')

    scope = cfg.config.get('google_oauth2_scope', ["https://www.googleapis.com/auth/userinfo.profile"])
    redirect_uri = cfg.config.get('sitename_ssl', 'localhost') + cfg.config.get('google_oauth2_register', '/register_google')
    token_url = cfg.config.get('google_oauth2_token_url', "https://accounts.google.com/o/oauth2/token")
    user_info_url = cfg.config.get('google_oauth2_user_info_url', 'https://www.googleapis.com/oauth2/v1/userinfo')

    (state, session_struct, session_struct2) = _get_session_info(request, params)

    content = _get_oauth2_info(client_id, client_secret, scope, redirect_uri, token_url, user_info_url, request, params)

    _post_register_google(content, state, session_struct, session_struct2, request, params)


def _post_register_google(content, state, session_struct, session_struct2, request, params):
    the_struct = util.json_loads(content)

    user_id = 'google_' + str(the_struct['id'])

    # save
    util_user.save_user(user_id, session_struct, session_struct2, {"google_id": the_struct['id'], 'name': the_struct['name'], 'given_name': the_struct['given_name'], 'family_name': the_struct['family_name'], 'extension': the_struct})

    cfg.logger.debug('user_info: content: (%s, %s) the_struct: (%s, %s)', content, content.__class__.__name__, the_struct, the_struct.__class__.__name__)

    # return
    _redirect_register(state)


def login_facebook(request, params):
    client_id = cfg.config.get('facebook_oauth2_client_id', '')

    scope = cfg.config.get('facebook_oauth2_scope', ["public_profile"])
    register_uri = cfg.config.get('sitename_ssl', 'localhost') + cfg.config.get('facebook_oauth2_register', '/register_facebook')
    authorization_base_url = cfg.config.get('facebook_oauth2_auth_url', "https://www.facebook.com/dialog/oauth")

    _login(client_id, scope, register_uri, authorization_base_url, request, params)


def register_facebook(request, params):
    client_id = cfg.config.get('facebook_oauth2_client_id', '')
    client_secret = cfg.config.get('facebook_oauth2_client_secret', '')

    scope = cfg.config.get('facebook_oauth2_scope', ["public_profile"])
    redirect_uri = cfg.config.get('sitename_ssl', 'localhost') + cfg.config.get('facebook_oauth2_register', '/register_facebook')
    token_url = cfg.config.get('facebook_oauth2_token_url', "https://graph.facebook.com/oauth/access_token")
    user_info_url = cfg.config.get('facebook_oauth2_user_info_url', 'https://graph.facebook.com/me?')

    (state, session_struct, session_struct2) = _get_session_info(request, params)

    content = _get_oauth2_info(client_id, client_secret, scope, redirect_uri, token_url, user_info_url, request, params, is_facebook=True)

    _post_register_facebook(content, state, session_struct, session_struct2, request, params)


def _post_register_facebook(content, state, session_struct, session_struct2, request, params):
    the_struct = util.json_loads(content)

    user_id = 'facebook_' + str(the_struct['id'])

    # save
    cfg.logger.debug('user_info: content: (%s, %s) the_struct: (%s, %s)', content, content.__class__.__name__, the_struct, the_struct.__class__.__name__)

    util_user.save_user(user_id, session_struct, session_struct2, {"facebook_id": the_struct['id'], 'name': the_struct.get('name', ''), 'given_name': the_struct['first_name'], 'family_name': the_struct['last_name'], 'extension': the_struct})

    # return
    _redirect_register(state)


def _login(client_id, scope, register_uri, authorization_base_url, request, params):
    (session_struct, session_struct2) = util_user.process_session(request)
    cfg.logger.debug('session_struct: %s session_struct2: %s', session_struct, session_struct2)

    the_path = params.get('url', '')
    the_timestamp = util.get_timestamp()

    cfg.logger.debug('params: %s the_path: %s', params, the_path)

    the_auth = OAuth2Session(client_id, scope=scope, redirect_uri=register_uri)

    authorization_url, state = the_auth.authorization_url(authorization_base_url, approval_prompt="auto")

    util.db_insert('login_info', {"state": state, "the_timestamp": the_timestamp, "params": params, "url": the_path})

    is_cron_remove_expire = cfg.config.get('is_cron_remove_expire', True)
    if not is_cron_remove_expire:
        expire_timestamp_session = cfg.config.get('expire_unix_timestamp_session', EXPIRE_UNIX_TIMESTAMP_SESSION) * 1000
        util.db_remove('login_info', {"the_timestamp": {"$lt": the_timestamp - expire_timestamp_session}})

    cfg.logger.debug('after authorization_url: authorization_url: %s state: %s', authorization_url, state)

    redirect(authorization_url)


def _get_session_info(request, params):
    (session_struct, session_struct2) = util_user.process_session(request)
    state = params.get('state', '')

    return (state, session_struct, session_struct2)


def _get_oauth2_info(client_id, client_secret, scope, redirect_uri, token_url, user_info_url, request, params, is_facebook=False):
    headers = dict(request.headers)
    cookies = dict(request.cookies)

    cfg.logger.debug('params: %s headers: %s cookies: %s', params, headers, cookies)

    the_auth = OAuth2Session(client_id, scope=scope, redirect_uri=redirect_uri)

    if is_facebook:
        the_auth = facebook_compliance_fix(the_auth)

    # fetch token
    #the_path = params.get('url', '')
    qs = urllib.urlencode(params)
    redirect_url = redirect_uri + '?' + qs

    token = the_auth.fetch_token(token_url, client_secret=client_secret, 
                           authorization_response=redirect_url)

    cfg.logger.debug('after fetch_token: token: (%s, %s)', token, token.__class__.__name__)

    # get user info
    r = the_auth.get(user_info_url)

    return r.content


def _redirect_register(state):
    login_info = util.db_find_one('login_info', {"state": state})
    util.db_remove('login_info', {"state": state})

    path_qs = login_info.get('url', '')

    redirect_url = cfg.config.get('sitename', 'localhost') + path_qs

    cfg.logger.warning('to redirect: redirect_url: %s', redirect_url)

    redirect(redirect_url)

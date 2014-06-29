# -*- coding: utf-8 -*-

from app.constants import S_OK, S_ERR
import random
import math
import base64
import time
import ujson as json

from app.constants import *
from app import cfg
from app import util

def is_valid_user(request):
    session = request.environ['beaker.session']
    if not session.has_key('value'):
        return (S_ERR, {})

    (error_code, user_info) = _session_user_mapping(session)
    if error_code != S_OK:
        return (error_code, user_info)

    return (S_OK, user_info)


def _session_user_mapping(session):
    session_key = session['value']
    session_list = [session_key]
    
    session_key2 = '' if not session.has_key('value2') else session['value2']
    if session_key2:
        session_list.append(session_key2)

    (error_code, db_results) = util.db_find('session_user_map', {"session_key": {"$in": session_list}})

    if error_code != S_OK:
        return (error_code, {})

    if not db_results:
        return (S_ERR, {})

    user_id = db_results[0]

    user_info = util.db_find_one('user_info', {"user_id": user_id})

    if not user_info: 
        return (S_ERR, {})

    if _is_to_refresh_google_token(user_info):
        _refresh_google_token(user_info)

    _check_refresh_session(session, session_key, session_key2, user_info)

    return (S_OK, user_info)


def _is_to_refresh_google_token(user_info):
    if user_info.get('user_type', '') != 'google':
        return False

    if user_info.get('token_refresh_timestamp', 0) < util.get_timestamp():
        return True

    return False


def _check_refresh_session(session, session_key, session_key2, user_info):
    the_timestamp = util.get_timestamp()
    user_id = user_info.get('user_id', '')

    (user_id, session_timestamp, session_id) = _deserialize_session_key(session_key)

    if the_timestamp - session_timestamp > EXPIRE_TIMESTAMP_SESSION_BLOCK:
        if not session_key2:
            session_key2 = _create_session_key(user_id)

        session_key3 = _create_session_key(user_id)

        session['value'] = session_key2
        session['value2'] = session_key3
        session.save()


def _create_session_key(user_id):
    session_key = _serialize_session_key(user_id, util.get_timestamp(), util.gen_random_string())

    util.db_update('session_user_map', {"session_key": session_key}, {"user_id": user_id})

    return session_key


def _deserialize_session_key(session_key):
    the_list = session_key.split('@')
    if not the_list:
        return ('', 0, '')

    user_id = the_list[0] if len(the_list) >= 1 else ''
    session_timestamp = util._int(the_list[1]) if len(the_list) >= 2 else 0
    session_id = the_list[2] if len(the_list) >= 3 else ''

    return (user_id, session_timestamp, session_id)


def _serialize_session_key(user_id, session_timestamp, session_id):
    return '@'.join([user_id, str(session_timestamp), session_id])

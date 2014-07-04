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

    user_info['session_value'] = session['value']
    user_info['session_value2'] = session['value2']

    return (S_OK, user_info)


def is_valid_user_without_check(request):
    session = request.environ['beaker.session']
    if not session.has_key('value'):
        process_session(request)
        session = request.environ['beaker.session']

    (error_code, user_info) = _session_user_mapping(session)

    user_info['session_value'] = session['value']
    user_info['session_value2'] = session['value2']

    return (S_OK, user_info)


def process_session(request):
    session = request.environ['beaker.session']
    session_struct = {}
    session_struct2 = {}
    the_timestamp = util.get_timestamp()

    if not session.has_key('value'):
        session_struct = _construct_session_struct(the_timestamp)
        session['value'] = session_struct.get('key', '')

        session_struct2 = _construct_session_struct(the_timestamp + 300)
        session['value2'] = session_struct2.get('key', '')
        session_key = _create_session_key()
        session_key2 = _create_session_key(offset_timestamp=300)
        session['value'] = session_key
        session['value2'] = session_key2
        session.save()
    else:
        session_key = session['value']
        session_key2 = session['value2']

        session_struct = _extract_session_struct_from_session_key(session_key)
        session_struct2 = _extract_session_struct_from_session_key(session_key2)

        session_timestamp = session_struct.get('the_timestamp', 0)
        session_timestamp2 = session_struct2.get('the_timestamp', 0)
        if the_timestamp - util._int(session_timestamp) >= 300:
            new_timestamp = max(the_timestamp, util._int(session_timestamp2) + 300)
            session_struct3 = _construct_session_struct(new_timestamp)

            session_struct = session_struct2
            session_struct2 = session_struct3
            session['value'] = session_struct.get('key', '')
            session['value2'] = session_struct2.get('key', '')
            session.save()

    return (session_struct, session_struct2)


def save_user(user_id, session_key, session_key2, user_info):
    util.db_update('user_info', {"user_id": user_id}, {"session_key": session_key, "session_key2": session_key2, "user_info": user_info})


def save_session_user_map(session_struct, user_id):
    session_key = session_struct.get('key', '')
    if not session_key:
        return

    util.db_update('session_user_map', {"session_key": session_key}, {'the_timestamp': session_struct.get('the_timestamp', 0), 'user_id': user_id})


def remove_session(session_struct):
    session_key = session_struct.get('key', '')
    if not session_key:
        return

    util.db_update('user_info', {'session_key': session_key}, {'session_key': ''}, multi=True)
    util.db_update('user_info', {'session_key2': session_key}, {'session_key2': ''}, multi=True)
    util.db_remove('session_user_map', {"session_key": session_key})


def _construct_session_struct(the_timestamp):
    return {"key": _create_session_key(), "the_timestamp": the_timestamp}


def _extract_session_struct_from_session_key(session_key):
    (session_timestamp, session_id) = _deserialize_session_key(session_key)

    return {"key": session_key, "the_timestamp": util._int(session_timestamp)}


def _session_user_mapping(session):
    session_key = session['value']
    session_list = [session_key]
    
    session_key2 = '' if not session.has_key('value2') else session['value2']
    if session_key2:
        session_list.append(session_key2)

    cfg.logger.warning('session_list: %s', session_list)
    (error_code, db_results) = util.db_find2('session_user_map', {"session_key": {"$in": session_list}})

    cfg.logger.warning('error_code: %s db_results: %s', error_code, db_results)

    if error_code != S_OK:
        return (error_code, {})

    if not db_results:
        return (S_ERR, {})

    user_id = db_results[0].get('user_id', '')

    user_info = util.db_find_one('user_info', {"user_id": user_id})

    if not user_info: 
        return (S_ERR, {})

    #if _is_to_refresh_google_token(user_info):
    #    _refresh_google_token(user_info)

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

    (session_timestamp, session_id) = _deserialize_session_key(session_key)

    if the_timestamp - session_timestamp > EXPIRE_TIMESTAMP_SESSION_BLOCK:
        if not session_key2:
            session_key2 = _create_session_key()

        session_key3 = _create_session_key(offset_timestamp=300)

        session['value'] = session_key2
        session['value2'] = session_key3
        session.save()


def _create_session_key(user_id=None, offset_timestamp=0):
    the_timestamp = util.get_milli_timestamp()
    the_timestamp += offset_timestamp
    session_key = _serialize_session_key(the_timestamp, util.gen_random_string())

    if user_id:
        util.db_update('session_user_map', {"session_key": session_key}, {"user_id": user_id, "the_timestamp": the_timestamp})

    return session_key


def _deserialize_session_key(session_key):
    the_list = session_key.split('@')
    if not the_list:
        return (0, '')

    session_timestamp = util._int(the_list[0]) if len(the_list) >= 1 else 0
    session_id = the_list[1] if len(the_list) >= 0 else ''

    return (session_timestamp, session_id)


def _serialize_session_key(session_timestamp, session_id):
    return '@'.join([str(session_timestamp), session_id])

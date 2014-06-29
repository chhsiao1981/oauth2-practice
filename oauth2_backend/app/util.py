# -*- coding: utf-8 -*-

from app.constants import *
import random
import math
import base64
import time
import ujson as json
import uuid

from app import cfg

def gen_random_string():
    return str(uuid.uuid4())


def _int(the_val, default=0):
    try:
        result = int(the_val)
    except Exception as e:
        cfg.logger.debug('unable to _int: the_val: %s e: %s', the_val, e)
        result = 0

    return result


def db_find(cf_name, key = None, fields={'_id': False}):
    result = []
    try:
        if key is None:
            result = cfg.config.get(cf_name).find(fields=fields)
        else:
            result = cfg.config.get(cf_name).find(key, fields=fields)
    except:
        cfg.logger.exception('unable to db_find: cf_name: %s key: %s', cf_name, key)
        result = None

    if result is None:
        result = []
    return list(result)


def db_find2(cf_name, key = None, fields={'_id': False}):
    error_code = S_OK
    result = []
    try:
        if key is None:
            result = cfg.config.get(cf_name).find(fields=fields)
        else:
            result = cfg.config.get(cf_name).find(key, fields=fields)
        error_code = S_OK
    except:
        cfg.logger.exception('unable to db_find: cf_name: %s key: %s', cf_name, key)
        result = None
        error_code = S_ERR

    if result is None:
        result = []

    return (error_code, list(result))


def get_timestamp():
    return int(time.time())


def db_find_it(cf_name, key = None, fields={'_id': False}):
    result = None
    try:
        if key is None:
            result = cfg.config.get(cf_name).find(fields=fields)
        else:
            result = cfg.config.get(cf_name).find(key, fields=fields)
    except:
        cfg.logger.exception('unable to db_find: cf_name: %s key: %s', cf_name, key)
        result = None

    return result


def db_find_one(cf_name, key, fields={'_id': False}):
    try:
        result = cfg.config.get(cf_name).find_one(key, fields=fields)
    except:
        cfg.logger.exception('unable to db_find_one: cf_name: %s key: %s', cf_name, key)
        result = None

    if result is None:
        result = {}

    return dict(result)


def db_update(cf_name, key, val, upsert=True):
    if not key or not val:
        #cfg.logger.exception('not key or val: key: %s val: %s', key, val)
        return

    #cfg.logger.debug('cf_name: %s key: %s val: %s', cf_name, key, val)
    result = {}
    try:
        result = cfg.config.get(cf_name).update(key, {'$set':val}, upsert=upsert, w=1)
    except Exception as e:
        cfg.logger.warning('unable to db_update: cf_name: %s key: %s val: %s e: %s', cf_name, key, val, e)
    return result


def db_insert(cf_name, val):
    error_code = S_OK
    cfg.logger.debug('cf_name: %s val: %s', cf_name, val)
    if not val:
        cfg.logger.error('not val: val: %s', val)
        return

    result = cfg.config.get(cf_name).insert(val)

    return result


def db_remove(cf_name, key):
    error_code = S_OK
    if cf_name in cfg._mongo_map:
        cfg.logger.error('remove error! CHECK CODE! cf_name: %s', cf_name)
        send_error_msg('db_remove error! CHECK_CODE! cf_name: %s' % (cf_name))
        return

    result = None
    try:
        result = cfg.config.get(cf_name).remove(key)
    except Exception as e:
        cfg.logger.error('unable to remove: cf_name: %s key: %s', cf_name, key)
        send_error_msg('unable to db_remove: cf_name: %s key: %s e: %s' % (cf_name, key, e))
        error_code = S_ERR
        result = None

    if error_code != S_OK:
        cfg._init_mongo()

    if result is None:
        result = {}

    return dict(result)


def json_dumps(json_struct, default_val='', sort_keys=False):
    result = default_val
    try:
        result = json.dumps(json_struct)
    except:
        cfg.logger.exception('unable to json_dumps: json_struct: %s', json_struct)

    return result


def json_loads(json_str, default_val={}):
    result = default_val
    try:
        result = json.loads(json_str)
    except:
        cfg.logger.exception('unable to json_loads: json_str: %s', json_str)
        result = default_val

    return result

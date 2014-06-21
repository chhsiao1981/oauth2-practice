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


def util.get_timestamp():
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


def json_dumps(json_struct, default_val='', sort_keys=False):
    result = default_val
    try:
        result = json.dumps(json_struct, sort_keys=sort_keys)
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

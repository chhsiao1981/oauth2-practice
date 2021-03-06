# -*- coding: utf-8 -*-

import ConfigParser
import logging
import logging.config
import random
import math
import base64
import time
import pymongo
from pymongo import MongoClient
import ujson as json

_LOGGER_NAME = "app"
logger = None
config = {}

_mongo_map = {
    'user_info': 'user_info',
    'session_user_map': 'session_user_map',
    'session_user_map2': 'session_user_map',
    'login_info': 'login_info',
}

_ensure_index = {
    'login_info': [('state', pymongo.ASCENDING)],
    'session_user_map': [('session_key', pymongo.ASCENDING)],
    'session_user_map2': [('the_timestamp', pymongo.ASCENDING)],
    'user_info': [('user_id', pymongo.ASCENDING)],
}

def init(params):
    init_cfg(params)

def init_cfg(params):
    '''params: parameters from main.py, currently including port and ini_filename'''
    _init_logger(params['ini_filename'])
    _init_ini_file(params['ini_filename'])
    _post_init_config(params)
    _post_json_config(config)
    _init_mongo()
    logger.info('config: %s', config)


def _init_mongo():
    global config
    global logger

    logger.warning('init_mongo: start')

    config['MONGO_SERVER_URL'] = "mongodb://" + config.get('mongo_server_hostname') + "/" + config.get('mongo_server')
    try:
        config['mongoServer'] = MongoClient(config.get('MONGO_SERVER_URL'), use_greenlets=True)[config.get('mongo_server')]
        for (key, val) in _mongo_map.iteritems():
            logger.debug('mongo: %s => %s', key, val)
            config[key] = config.get('mongoServer')[val]
    except:
        logger.exception('')

        for (key, val) in _mongo_map.iteritems():
            config[key] = None

    for (key, val) in _ensure_index.iteritems():
        config[key].ensure_index(val)


def _init_logger(ini_file):
    '''logger'''
    global logger
    logger = logging.getLogger(_LOGGER_NAME)
    logging.config.fileConfig(ini_file, disable_existing_loggers=False)


def _init_ini_file(ini_file):
    '''...'''
    global config
    section = 'app:main'

    config_parser = ConfigParser.SafeConfigParser()
    config_parser.read(ini_file)
    options = config_parser.options(section)
    config = {option: __init_ini_file_parse_option(option, section, config_parser) for option in options}


def __init_ini_file_parse_option(option, section, config_parser):
    try:
        val = config_parser.get(section, option)
    except Exception as e:
        logger.warning(str(e))
        val = ''
    return val


def _post_init_config(params):
    '''...'''
    global config
    for k in params.keys():
        v = params[k]
        if k in config:
            logger.warning('params will be overwrite: key: %s origin: %s new: %s', k, config[k], v)
        config[k] = v


def _post_json_config(config):
    logger.debug('start: config: %s', config)
    for k, v in config.iteritems():
        if v.__class__.__name__ != 'str':
            continue

        orig_v = v
        try:
            config[k] = json.loads(v)
        except:
            config[k] = orig_v

    logger.debug('end: config: %s', config)

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

from app import cfg
from app.gevent_server import GeventServer

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

    run(app, host='0.0.0.0', port=cfg.config.get('port'), server=GeventServer)

# -*- coding: utf-8 -*-
"""
    http://werkzeug-docs-cn.readthedocs.io/zh_CN/latest/tutorial.html#module-routing
    Werkzeug 教程，我们将会实现一个类似 TinyURL 的网站来储存 URLS。
    我们 将会使用的库有模板引擎 Jinja 2，数据层支持 redis ，当然还有 
    WSGI 协议层 Werkzeug。
"""



import os
import redis
import urlparse
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader


class Shortly():

    def __init__(self, config):
        self.redis = redis.Redis(config['redis_host'], config['redis_port'])

    def dispatch_request(self, request):
        return Response('Hello World!')

    def wsgi_app(self, environ, start_response):
        request = Response(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi_app(environ, start_response)

def create_app(redis_host='localhost', redis_port=6379, with_static=True):
    app = Shortly({
        'redis_host': redis_host,
        'redis_port': redis_port
        })
    if with_static:
        # 通过 WSGI 中间件输出 static 目录的文件
        app.wsgi_app = SharedDataMiddleware(app.wsgi_app, {
            '/static': os.path.join(os.path.dirname(__file__), 'static')
            })
    return app

    
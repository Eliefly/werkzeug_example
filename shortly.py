# -*- coding: utf-8 -*-
"""
    http://werkzeug-docs-cn.readthedocs.io/zh_CN/latest/tutorial.html#module-routing
    Werkzeug 教程，我们将会实现一个类似 TinyURL 的网站来储存 URLS。
    我们 将会使用的库有模板引擎 Jinja 2，数据层支持 redis ，当然还有 
    WSGI 协议层 Werkzeug。
"""



import os
import redis
#import urlparse     # The urlparse module is renamed to urllib.parse in Python 3
from urllib.parse import urlparse
from werkzeug.wrappers import Request, Response
from werkzeug.routing import Map, Rule
from werkzeug.exceptions import HTTPException, NotFound
from werkzeug.wsgi import SharedDataMiddleware
from werkzeug.utils import redirect
from jinja2 import Environment, FileSystemLoader


class Shortly():

    def __init__(self, config):
        self.redis = redis.Redis(config['redis_host'], config['redis_port'])
        template_path = os.path.join(os.path.dirname(__file__), 'templates')
        self.jinja_env = Environment(loader=FileSystemLoader(template_path),
                                    autoescape=True)
        self.url_map = Map([
            Rule('/', endpoint='new_url'),
            Rule('/<short_id>', endpoint='follow_short_link'),
            Rule('/<short_id>+', endpoint='short_link_details')
        ])

    def render_template(self, template_name, **context):
        t = self.jinja_env.get_template(template_name)
        return Response(t.render(context), mimetype='text/html')

    def dispatch_request(self, request):
        # return Response('Hello World!')
        # 将 RUL 绑定到目前的环境返回一个 URLAdapter 。适配器 可以用于匹配请求也可以翻转 URLS。
        adapter = self.url_map.bind_to_environ(request.environ)
        try:
            endpoint, values = adapter.match()  # 匹配方法将会返回 endpoint 和一个 URL 值字典。
            # 所有的 URL 参数做作为关键字参数调用 on_ + endpoint 函数可以返回响应对象
            return getattr(self, 'on_' + endpoint)(request, **values)   
        except HTTPException(e):
            return e

    def on_new_url(self, request):
        error = None
        url = ''
        if request.method == 'POST':
            # 从 request 中获取 url
            url = request.form['url']
            if not is_valid_url(url):
                error = 'Please enter a valid URL'
            else:
                short_id = self.insert_url(url)
                return redirect('/%s+' % short_id)
        return self.render_template('new_url.html', error=error, url=url)

    def on_follow_short_link(self, request, short_id):
        link_target = self.redis.get('url-target:' + short_id)
        if link_target is None:
            raise NotFound()
        self.redis.incr('click-count:' + short_id)
        return redirect(link_target)

    def on_short_link_details(self, request, short_id):
        link_target = self.redis.get('url-target:' + short_id)
        if link_target is None:
            raise NotFound()
        click_count = int(self.redis.get('click-count:' + short_id) or 0)
        return self.render_template('short_link_details.html',
            link_target=link_target,
            short_id=short_id,
            click_count=click_count
        )


    def insert_url(self, url):
        short_id = self.redis.get('reverse-url:' + url)
        if short_id is not None:
            return short_id
        url_num = self.redis.incr('last-url-id')
        short_id = base36_encode(url_num)
        self.redis.set('url-target:' + short_id, url)
        self.redis.set('reverse-url' + url, short_id)
        return short_id


    def wsgi_app(self, environ, start_response):
        '''
         wsgi_app 实际上创建了一个 Request 对象, 之后通过 
         dispatch_request 调用 Request 对象然后给 WSGI 应
         用返回一个 Response 对象。
         '''
        request = Request(environ)
        response = self.dispatch_request(request)
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        # __call__ 方法直接调 用 wsgi_app
        return self.wsgi_app(environ, start_response)

def is_valid_url(url):
    parts = urlparse(url)
    return parts.scheme in ('http', 'https')

def base36_encode(number):
    assert number >= 0, 'positive integer required'
    if number == 0:
        return 0
    base36 = []
    while number != 0:
        number, i = divmod(number, 36)
        base36.append('0123456789abcdefghijklmnopqrstuvwxyz'[i])
    return ''.join(reversed(base36))

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

if __name__ == '__main__':
    from werkzeug.serving import run_simple
    app = create_app()
    run_simple('127.0.0.1', 5000, app, use_debugger=True, use_reloader=True)
    

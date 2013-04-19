#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/18 16:17:25
#   Desc    :
#
from __future__ import absolute_import

import ssl
import time
import socket
import urllib
import urllib2
import httplib
import urlparse
import tempfile
import cookielib
import threading
import mimetools
import mimetypes
import itertools

from functools import partial
from tornado.ioloop import IOLoop


class Form(object):
    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        self.content_type = 'multipart/form-data; boundary=%s' % self.boundary
        return

    def get_content_type(self):
        return self.content_type

    def add_field(self, name, value):
        self.form_fields.append((str(name), str(value)))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        body = fileHandle.read()
        if mimetype is None:
            mimetype = ( mimetypes.guess_type(filename)[0]
                         or
                         'applicatioin/octet-stream')
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        parts = []
        part_boundary = '--' + self.boundary

        parts.extend(
            [ part_boundary,
             'Content-Disposition: form-data; name="%s"' % name,
             '',
             value,
             ]
            for name, value in self.form_fields)
        if self.files:
            parts.extend([
                part_boundary,
                'Content-Disposition: form-data; name="%s"; filename="%s"' %\
                (field_name, filename),
                'Content-Type: %s' % content_type,
                '',
                body,
            ] for field_name, filename, content_type, body in self.files)

        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)


class HTTPSock(object):
    """ 构建支持Cookie的HTTP socket
    供可复用的I/O模型调用"""
    def __init__(self):
        cookiefile = tempfile.mktemp()
        self.cookiejar = cookielib.MozillaCookieJar(cookiefile)

    def make_get_url(self, url, params):
        return "{0}?{1}".format(url, urllib.urlencode(params))

    def make_request(self, url, form = None):
        """ 根据url 参数 构建 urllib2.Request """
        request = urllib2.Request(url)
        if isinstance(form, Form):
            request.add_header("Content-Type", form.get_content_type())
            request.add_header("Content-Length", len(str(form)))
            request.add_data(str(form))
        elif isinstance(form, (dict, list, tuple)):
            params = urllib.urlencode(form)
            request = urllib2.Request(url, params)
            request.add_header("Content-Type",
                                "application/x-www-form-urlencoded")

        self.cookiejar.add_cookie_header(request)
        request.headers.update(request.unredirected_hdrs)
        return request

    def make_response(self, sock, req):
        """ 根据socket和urlib2.Request 构建Response """
        sock.setblocking(True)
        data = req.get_data()
        method = "POST" if data else "GET"
        r = httplib.HTTPResponse(sock, 0, strict = 0, method = method,
                                 buffering=True)
        r.begin()

        r.recv = r.read
        fp = socket._fileobject(r, close=True)

        resp = urllib.addinfourl(fp, r.msg, req.get_full_url())
        resp.code = r.status
        resp.msg = r.reason
        self.cookiejar.extract_cookies(resp, req)
        self.cookiejar.save()
        return resp


    def make_http_sock_data(self, request):
        """ 根据urllib2.Request 构建socket和用于发送的HTTP源数据 """
        url = request.get_full_url()
        headers = request.headers
        data = request.get_data()
        parse = urlparse.urlparse(url)
        host, port = urllib.splitport(parse.netloc)
        typ = parse.scheme
        port = port if port else getattr(httplib, typ.upper() + "_PORT")
        data =  self.get_http_source(parse, data, headers)
        if hasattr(self, "do_" + typ):
            return getattr(self, "do_"+typ)(host, port), data

    def do_http(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, int(port)))
        sock.setblocking(0)
        return sock

    def do_https(self, host, port, keyfile = None, certfile = None):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, int(port)))
        sock = ssl.wrap_socket(sock, keyfile, certfile)
        sock.setblocking(0)
        return sock

    def get_http_source(self, parse, data, headers):
        path = parse.path
        query = parse.query
        path = path + "?" + query if query else path
        path = path if path else "/"
        method = "POST" if data else "GET"
        _buffer= ["{0} {1} HTTP/1.1".format(method, path)]
        e_headers = [(k.lower(), v) for k, v in headers.items()]
        headers = []
        headers.append(("Host", parse.netloc))
        headers.append(("Connection", "keep-alive"))
        headers.append(("Accept", "*/*"))
        #headers.append(("Accept-Charset", "UTF-8,*;q=0.5"))
        #headers.append(("Accept-Encoding", "gzip,deflate,sdch"))
        #headers.append(("Accept-Language", "zh-CN,zh;q=0.8"))
        headers.append(("User-Agent", "Mozilla/5.0 (X11; Linux x86_64)"\
                        " AppleWebKit/537.11 (KHTML, like Gecko)"\
                        " Chrome/23.0.1271.97 Safari/537.11"))
        headers+= e_headers
        if data:
            headers.append(("Content-Length",   len(data)))
        for key, value in headers:
            _buffer.append("{0}: {1}".format(key.title(), value))
        _buffer.extend(("", ""))
        result = "\r\n".join(_buffer)
        if isinstance(data, str):
            result += data
        return result

    @property
    def cookie(self):
        return self.cookiejar._cookies

class HTTPStream(object):
    """ HTTP流
    应当按照如下方法调用:
        import urllib2

        http_stream = HTTPStream.instance()
        request = urllib2.Request("http://www.linuxzen.com")
        def read_callback(resp):
            print resp.read()
        http_stream.add_request(request, read_callback)
        http_stream.start()
    """
    _ioloop = IOLoop.instance()
    _http_sock = HTTPSock()
    cookie = _http_sock.cookie
    cookiejar = _http_sock.cookiejar
    _instance = None

    def __init__(self, ioloop, http_sock):
        self.ioloop = ioloop
        self.http_sock = http_sock
        self.fd_map = {}
        self.fd_request_map = {}

    @classmethod
    def instance(cls):
        if not cls._instance:
            cls._instance = cls(cls._ioloop, cls._http_sock)
        return cls._instance


    def make_get_request(self, url, params = None):
        if params:
            url = self.make_get_url(url, params)
        return self.http_sock.make_request(url)

    def make_post_request(self, url, params):
        return self.http_sock.make_request(url, params)

    def make_get_url(self, url, params):
        return self.http_sock.make_get_url(url, params)

    def add_request(self, request, readback = None):
        sock, data = self.http_sock.make_http_sock_data(request)
        fd = sock.fileno()
        self.fd_map[fd] = sock
        self.fd_request_map[fd] = request
        callback = partial(self._handle_events, request, data, readback)
        self.ioloop.add_handler(fd, callback, IOLoop.WRITE)


    def add_delay_request(self, request, readback, delay = 60):
        if isinstance(threading.currentThread(), threading._MainThread):
            raise threading.ThreadError, "Can't run this function in _MainThread"

        time.sleep(delay)
        self.add_request(request, readback)


    def _handle_events(self, request, data, readback, fd, event):
        """ 用于处理Tornado事件
        Arguments:
            `request`   -   urllib.Request
            `data`      -   socket要写入的数据
            `readback`  -   读取函数
            以上参数应当使用partial封装然后将此方法作为IOLoop.add_handler的callback
            `fd`        -   IOLoop传递 文件描述符
            `event`     -   IOLoop传递 tornado
        """
        s = self.fd_map[fd]

        if event & IOLoop.READ:
            try:
                resp = self.http_sock.make_response(s, request)
            except httplib.BadStatusLine:
                import sys
                sys.exit(1)
            args = readback(resp)
            if args and len(args) == 3:
                t = threading.Thread(target = self.add_delay_request, args = args)
                t.setDaemon(True)
                t.start()

            if args and len(args) == 2:
                self.add_request(*args)
            self.ioloop.remove_handler(fd)

        if event & IOLoop.WRITE:
            s.sendall(data)
            if readback:
                self.ioloop.update_handler(fd, IOLoop.READ)
            else:
                self.ioloop.remove_handler(fd)

        if event & IOLoop.ERROR:
            pass

    def start(self):
        self.ioloop.start()

if __name__ == "__main__":
    http_stream = HTTPStream.instance()
    request = urllib2.Request("http://www.linuxzen.com")
    def read_callback(resp):
        print resp.read()
    http_stream.add_request(request, read_callback)
    http_stream.start()

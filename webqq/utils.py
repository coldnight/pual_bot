#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/02/28 16:37:58
#   Desc    :   工具类函数
from __future__ import absolute_import, division

import Queue
import logging
import threading
import functools
import urllib2, urllib, cookielib
import mimetools
import mimetypes
import itertools


def get_logger(name = None, level = logging.DEBUG):
    if not name: name = 'qxbot'
    logger = logging.getLogger(name)
    hdl = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    hdl.setFormatter(fmt)
    handler = hdl
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(level) # change to DEBUG for higher verbosity
    logger.propagate = False
    return logger

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


class HttpHelper(object):
    def __init__(self, url = None, form = None, method = 'GET', jar = None):
        self.logger = get_logger()
        self._url = url
        self._form = form
        self._method = method
        if jar is None:
            self._cookie_file = r'/tmp/cookie.txt'
            self._cookiejar = cookielib.MozillaCookieJar(self._cookie_file)
        else:
            self._cookiejar = jar
        self.http_cookie = urllib2.HTTPCookieProcessor( self._cookiejar)
        self._opener = urllib2.build_opener(self.http_cookie)
        if url:
            self.make_request()

    def make_request(self):
        self.request = urllib2.Request(self._url)
        if isinstance(self._form, Form):
            self.add_header("Content-Type", self._form.get_content_type())
            self.add_header("Content-Length", len(str(self._form)))
            self.request.add_data(str(self._form))
        elif isinstance(self._form, (dict, list, tuple)):
            params = urllib.urlencode(self._form)
            if self._method == "GET":
                url = "{0}?{1}".format(self._url, params)
                self.request = urllib2.Request(url)
            else:
                self.request = urllib2.Request(self._url, params)
                self.request.add_header("Content-Type",
                                        "application/x-www-form-urlencoded")

        self.request.add_header("Accept", "*/*")
        self.request.add_header("Connection", "keep-alive")
        self.request.add_header("Accept-Charset", "UTF-8,*;q=0.5")
        self.request.add_header("Accept-Encoding", "gzip,deflate,sdch")
        self.request.add_header("Accept-Language", "zh-CN,zh;q=0.8")
        self.add_header("User-Agent", "Mozilla/5.0 (X11; Linux x86_64)"
                        "AppleWebKit/537.11 (KHTML, like Gecko)"
                        " Chrome/23.0.1271.97 Safari/537.11a")

    @property
    def cookie(self):
        self._cookiejar.save()
        return self._cookiejar._cookies

    def add_header(self, key, val):
        self.request.add_header(key, val)

    def change(self, url, form = {}, method = 'GET'):
        self._url = url
        self._form = form
        self._method = method
        self.make_request()
        return self

    def open(self):
        try:
            params = dict(self._form)
        except:
            params = self._form
        logbody = "{0} {1} params {2!r}".format(self._method, self._url, params)
        self.logger.debug(logbody)
        res = self._opener.open(self.request, timeout = 3)
        return res

def upload_file(filename, path):
    """ 上传文件
    - `path`      文件路径
    """
    form = Form()
    filename = filename.encode("utf-8")
    form.add_file(fieldname='uploadfile', filename=filename,
                    fileHandle=open(path))
    helper = HttpHelper("http://paste.linuxzen.com", form)
    return helper.open()

class ThreadPool(object):
    """ 线程池
        启动相应的线程数,提供接口添加任务,任务为函数
        因为线程池时刻都有可能用到所以不做清理
        `thread_num`  - 初始化线程数
    """
    def __init__(self, thread_num = 1):
        self._thread_num = thread_num
        self._jobs_queue = Queue.Queue()
        self._threads = []

        return

    def add_job(self, func, *args, **kwargs):
        """ 添加任务 """
        func = functools.partial(func, *args, **kwargs)
        self._jobs_queue.put(func)

        return

    def worker(self):
        """ 工作线程
            使用Queue阻塞
            因为传入的函数已经做了相应的错误处理,
            所以在此不做进一步错误处理
        """
        while True:
            func = self._jobs_queue.get()
            func()

    def start(self):
        """ 根据线程数启动工作线程 """
        target = self.worker
        for i in xrange(0, self._thread_num):
            name = 'thread_pool-' + str(i)
            t = threading.Thread(target = target, name = name)
            t.setDaemon(True)
            self._threads.append(t)
            t.start()

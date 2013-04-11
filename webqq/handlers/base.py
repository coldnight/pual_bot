#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:04:50
#   Desc    :   WebQQ Base Handler
#
import socket
import threading
from ..http_socket import HTTPSock
from ..mainloop.interfaces import IOHandler, HandlerReady
from ..webqqevents import RetryEvent, RemoveEvent


class WebQQHandler(IOHandler):
    """ WebQQ Handler 基类, 所有Handler必须继承此基类
    Arguments:
        `webqq`      -           webqq.webqq.WebQQ 的实例
        `req`        -           urllib2.Request实例, 如传递则不构建新的请求
        `*args` `**kwargs` -     传递给初始化函数的参数
    """
    http_sock = HTTPSock()
    def __init__(self, webqq, req = None, *args, **kwargs):
        self.req = req
        self._readable = False
        self._writable = True
        self.webqq = webqq
        self.lock = threading.RLock()
        self._cond = threading.Condition(self.lock)
        self.old_fileno = None
        self.retry_args = []             # 重试时传递的参数
        self.retry_kwargs = {}           # 重试时传递的关键字形参
        self.setup(*args, **kwargs)      # 子类初始化接口

    def fileno(self):
        with self.lock:
            if self.sock is not None:
                return self.sock.fileno()

        return None

    def is_readable(self):
        return self.sock is not None and self._readable

    def wait_for_readability(self):
        with self.lock:
            while True:
                if self.sock is None or not self._readable:
                    return False
                else:
                    return True
            self._cond.wait()


    def is_writable(self):
        with self.lock:
            return self.sock and self.data and self._writable

    def wait_for_writability(self):
        with self.lock:
            while True:
                if self.sock and self.data and self._writable:
                    return True
                else:
                    return False
            self._cond.wait()

    def prepare(self):
        return HandlerReady()

    def handle_read(self):
        pass

    def handle_hup(self):
        with self.lock:
            pass

    def handle_write(self, *args, **kwargs):
        """ 处理socket 写, 所有参数用于传递给重试时使用 """
        self._writable = False
        try:
            self.sock.sendall(self.data)
        except socket.error, err:
            self.retry_self(err)
        else:
            self._readable = True

    def handle_err(self):
        with self.lock:
            self.sock.close()
            self.sock = None

    def handle_nval(self):
        if self.sock is None:
            return

    def close(self):
        self.sock.close()

    def remove_self(self):
        """ 移除自身的handler """
        self._writable = False
        self._readable = False
        self.webqq.event(RemoveEvent(self))

    def make_http_resp(self):
        """ 构造http Response """
        try:
            return self.http_sock.make_response(self.sock, self.req, self.method)
        except Exception, err:
            self.retry_self(err)

    def retry_self(self, err):
        self.webqq.event(RetryEvent(self.__class__, self.req, self, err,
                                *self.retry_args, **self.retry_kwargs))

    def make_http_sock(self, url, params, method, headers = {}):
        """ 构造HTTP SOCKET
        Arguments:
            `url`      -        请求的url
            `params`   -        请求的参数  {} or [(key, value), ...]
            `method`   -        请求的方法
            `headers`  -        请求的额外头部
        """
        self.method = method
        if not self.req:
            self.req = self.http_sock.make_request(url, params, method)
            if headers:
                for key, value in headers.items():
                    self.req.add_header(key, value)
        try:
            self.sock, self.data = self.http_sock.make_http_sock_data(self.req)
        except socket.error, err:
            self.retry_self(err)
            self._writable = False
            self.sock = None
            self.data = None

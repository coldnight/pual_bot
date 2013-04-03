#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:25:11
#   Desc    :   WebQQ心跳
#
import socket
from .base import WebQQHandler
from ..webqqevents import RetryEvent, WebQQHeartbeatEvent

class HeartbeatHandler(WebQQHandler):
    """ 心跳 """
    def setup(self, delay = 0):
        self._readable = False
        self.delay = delay

        url = "http://web.qq.com/web2/get_msg_tip"
        params = [("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                    ("rc", self.webqq.rc), ("lv", 2),
                ("t", int(self.webqq.hb_last_time * 1000))]
        self.make_http_sock(url, params, "GET", {})

    def handle_write(self):
        self._writable = False
        try:
            self.sock.sendall(self.data)
        except socket.error, err:
            self.webqq.event(RetryEvent(HeartbeatHandler, self.req, self, err))
        self.webqq.event(WebQQHeartbeatEvent(self), self.delay)

    def is_readable(self):
        return False

    def is_writable(self):
        with self.lock:
            return self.sock and self.data and self._writable

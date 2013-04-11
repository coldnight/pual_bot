#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:16:17
#   Desc    :   检查是否需要验证码的handler
#
import random
from .base import WebQQHandler
from ..webqqevents import CheckedEvent

class CheckHandler(WebQQHandler):
    """ 检查是否需要验证码
    url : http://check.ptlogin2.qq.com/check
    接口返回:
        ptui_checkVC('0','!PTH','\x00\x00\x00\x00\x64\x74\x8b\x05');
        第一个参数表示状态码, 0 不需要验证, 第二个为验证码, 第三个为uin
    """
    def setup(self):
        url = "http://check.ptlogin2.qq.com/check"
        params = {"uin":self.webqq.qid, "appid":self.webqq.aid,
                  "r" : random.random()}
        self.make_http_sock(url, params, "GET")

    def handle_read(self):
        self._readable = False
        resp = self.http_sock.make_response(self.sock, self.req, self.method)
        self.webqq.check_data = resp.read()
        self.webqq.event(CheckedEvent(self.webqq.check_data, self))

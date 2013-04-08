#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:28:36
#   Desc    :   获取消息
#
import json
import socket
import httplib
from .base import WebQQHandler
from ..webqqevents import  WebQQPollEvent, WebQQMessageEvent, ReconnectEvent

class PollHandler(WebQQHandler ):
    """ 获取消息 """
    def setup(self):
        method = "POST"
        url = "http://d.web2.qq.com/channel/poll2"
        params = [("r", '{"clientid":"%s", "psessionid":"%s",'
                '"key":0, "ids":[]}' % (self.webqq.clientid,
                                        self.webqq.psessionid)),
                ("clientid", self.webqq.clientid),
                ("psessionid", self.webqq.psessionid)]
        headers = {"Referer": "http://d.web2.qq.com/proxy.html?v="
                            "20110331002&callback=1&id=2"}
        self.make_http_sock(url, params, method, headers)


    def handle_read(self):
        self._readable = False
        try:
            resp = self.http_sock.make_response(self.sock, self.req, self.method)
            tmp = resp.read()
            data = json.loads(tmp)
            if data:
                if data.get("retcode") == 121:
                    self.webqq.event(ReconnectEvent(self))
                self.webqq.event(WebQQPollEvent(self))
                self.webqq.event(WebQQMessageEvent(data, self))
        except ValueError:
            pass
        except socket.error:
            self.webqq.event(WebQQPollEvent(self))
        except httplib.BadStatusLine:
            pass

    def is_writable(self):
        with self.lock:
            return self.sock and self.data and self._writable

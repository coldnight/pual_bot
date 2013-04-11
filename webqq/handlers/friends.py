#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/02 16:52:29
#   Desc    :   获取好友列表
#
import json
from .base import WebQQHandler
from ..webqqevents import WebQQRosterUpdatedEvent, FriendsUpdatedEvent

class FriendsHandler(WebQQHandler):
    """ 获取好友列表
    URL:
        http://s.web2.qq.com/api/get_user_friends2
    METHOD:
        POST
    PARAMS:
        {r:{"h":"hello", "vfwebqq":""}}
    HEADER:
        Referer:http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1
    """

    def setup(self):
        self.method = "POST"

        url = "http://s.web2.qq.com/api/get_user_friends2"
        params = [("r", json.dumps({"h":"hello",
                                    "vfwebqq":self.webqq.vfwebqq}))]
        headers = {
            "Referer":
            "http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1"}

        self.make_http_sock(url, params, "POST", headers)

    def handle_read(self):
        self._readable = False

        try:
            resp = self.http_sock.make_response(self.sock, self.req, self.method)
            data = json.loads(resp.read())
        except ValueError, err:
            self.retry_self(err)
        else:
            self.remove_self()
            self.webqq.event(FriendsUpdatedEvent(self, data))
            self.webqq.fm_updated = True
            if self.webqq.gm_updated:
                self.webqq.event(WebQQRosterUpdatedEvent(self))

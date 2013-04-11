#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:34:11
#   Desc    :   组列表
#
import json
import httplib
from .base import WebQQHandler
from ..webqqevents import  GroupListEvent

class GroupListHandler(WebQQHandler):
    def setup(self, delay = 0):
        self.delay = delay
        url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
        params = [("r", '{"vfwebqq":"%s"}' % self.webqq.vfwebqq),]
        headers = {"Origin": "http://s.web2.qq.com",
                    "Referer": "http://s.web2.qq.com/proxy.ht"
                                "ml?v=20110412001&callback=1&id=1"}
        self.make_http_sock(url, params, "POST", headers)


    def handle_read(self):
        self._readable = False

        try:
            resp = self.make_http_resp()
            tmp = resp.read()
            data = json.loads(tmp)
        except ValueError, err:
            self.retry_self(err)
        except httplib.BadStatusLine, err:
            self.retry_self(err)
        else:
            self.webqq.event(GroupListEvent(self, data), self.delay)

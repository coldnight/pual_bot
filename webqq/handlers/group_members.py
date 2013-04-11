#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:36:57
#   Desc    :   组成员
#
import time
import json
import socket
from .base import WebQQHandler
from ..webqqevents import RetryEvent, WebQQRosterUpdatedEvent, GroupMembersEvent

class GroupMembersHandler(WebQQHandler):
    """ 获取组成员
    URL:
        "http://s.web2.qq.com/api/get_group_info_ext2"
    METHOD:
        GET
    PARAMS:
        {
            gcode:gcode,  // 群代码
            vfwebqq: vfwebqq,
            t:time.time()  // 当前时间
        }
    HEADER:
        Referer:http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3"
    """
    def setup(self, gcode, done = False):
        """ 初始化
        Arguments:
            `gcode`  -   群代码
            `done`   -   是否是最后一个
        """
        self.done = done
        self.gcode = gcode
        self.retry_args = (self.gcode, self.done)

        url = "http://s.web2.qq.com/api/get_group_info_ext2"
        params = [("gcode", gcode),("vfwebqq", self.webqq.vfwebqq),
                ("t", int(time.time()))]
        headers = {
            "Referer":
            "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3"
        }
        self.make_http_sock(url, params, "GET", headers, self.gcode,
                                self.done)

    def handle_write(self):
        super(GroupMembersHandler, self).handle_write(self.gcode, self.done)

    def handle_read(self):
        self._readable = False

        try:
            resp = self.http_sock.make_response(self.sock, self.req, self.method)
            self.sock.setblocking(4)   # 有chunked数据 阻塞一下
            tmp = resp.read()
            self.sock.setblocking(0)
            data = json.loads(tmp)
        except ValueError, err:
            self.retry_self(err)
        else:
            self.webqq.event(GroupMembersEvent(self, data, self.gcode))
            if self.done:
                self.webqq.gm_updated = True
                if self.webqq.fm_updated:
                    self.webqq.event(WebQQRosterUpdatedEvent(self))

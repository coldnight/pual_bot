#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:31:30
#   Desc    :   组消息
#
import json
import socket
from .base import WebQQHandler
from ..webqqevents import RetryEvent

class GroupMsgHandler(WebQQHandler):
    def setup(self, group_uin = None, content = None):
        self.group_uin = group_uin
        self.content = content
        assert group_uin
        assert content
        gid = self.webqq.group_map.get(group_uin).get("gid")
        content = self.webqq.make_msg_content(content)
        r = {"group_uin": gid, "content": content,
            "msg_id": self.webqq.msg_id, "clientid": self.webqq.clientid,
            "psessionid": self.webqq.psessionid}
        self.webqq.msg_id += 1
        url = "http://d.web2.qq.com/channel/send_qun_msg2"
        params = [("r", json.dumps(r)), ("sessionid", self.webqq.psessionid),
                ("clientid", self.webqq.clientid)]
        headers = {"Referer": "http://d.web2.qq.com/proxy.html"}
        self.make_http_sock(url, params, "POST", headers, self.group_uin,
                            self.content)

    def handle_write(self):
        self._writable = False
        if self.content != self.webqq.last_msg.get(self.group_uin)  :
            self.webqq.last_msg[self.group_uin] = self.content
            try:
                self.sock.sendall(self.data)
            except socket.error, err:
                self.webqq.event(RetryEvent(self.__class__, self.req, self,
                                           err, self.group_uin, self.content))
            else:
                self.remove_self()

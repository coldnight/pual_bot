#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/02 18:00:47
#   Desc    :   给朋友发送消息
#
import json
from .base import WebQQHandler

class BuddyMsgHandler(WebQQHandler):
    """
    URL:
        http://d.web2.qq.com/channel/send_buddy_msg2

    METHOD:
        POST

    PARAMS:
        {
            "r":{
                "to":to,
                "face":564,
                "content":[],
                "msg_id":msg_id,
                "clientid":clientid,
                "psessionid":psessionid
                }
            "clientid":clientid,
            "psessionid": psessionid,
        }

    HEADERS:
        Referer:http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3
    """
    def setup(self, to_uin = None, content = None):
        """ 初始化Handler
        Arguments:
            `uin`         -       好友的uin
            `content`     -       发送内容
        """
        self.to_uin = to_uin
        self.content = self.webqq.make_msg_content(content)

        url = "http://d.web2.qq.com/channel/send_buddy_msg2"

        r = {"to":self.to_uin, "face":564, "content":self.content,
             "clientid":self.webqq.clientid, "msg_id": self.webqq.msg_id,
             "psessionid": self.webqq.psessionid}
        self.webqq.msg_id += 1
        params = [("r",json.dumps(r)), ("clientid",self.webqq.clientid),
                  ("psessionid", self.webqq.psessionid)]
        method = "POST"
        headers = {
            "Referer":
            "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3",
            "Origin":"http://d.web2.qq.com"
        }

        self.make_http_sock(url, params, method, headers)

    def handle_write(self):
        super(BuddyMsgHandler, self).handle_write()
        self.remove_self()

#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:23:10
#   Desc    :   登录处理器
#
import json
from .base import WebQQHandler
from ..webqqevents import WebQQLoginedEvent

class LoginHandler(WebQQHandler):
    """ 利用前几步生成的数据进行登录
    :接口返回示例
        {u'retcode': 0,
        u'result': {
            'status': 'online', 'index': 1075,
            'psessionid': '', u'user_state': 0, u'f': 0,
            u'uin': 1685359365, u'cip': 3673277226,
            u'vfwebqq': u'', u'port': 43332}}
        保存result中的psessionid和vfwebqq供后面接口调用
    """
    def setup(self):
        url = "http://d.web2.qq.com/channel/login2"
        params = [("r", '{"status":"online","ptwebqq":"%s","passwd_sig":"",'
                '"clientid":"%d","psessionid":null}'\
                % (self.webqq.ptwebqq, self.webqq.clientid)),
                ("clientid", self.webqq.clientid),
                ("psessionid", "null")
                ]

        headers = {"Referer": "http://d.web2.qq.com/proxy.html?"
                            "v=20110331002&callback=1&id=3",
                   "Origin": "http://d.web2.qq.com"}
        self.make_http_sock(url, params, "POST", headers)


    def handle_read(self):
        self._readable = False
        resp = self.http_sock.make_response(self.sock, self.req, self.method)
        tmp = resp.read()
        data = json.loads(tmp)
        self.webqq.vfwebqq = data.get("result", {}).get("vfwebqq")
        self.webqq.psessionid = data.get("result", {}).get("psessionid")
        self.webqq.event(WebQQLoginedEvent(self))

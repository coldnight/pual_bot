#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 11:20:02
#   Desc    :   登录前的操作
#
from .base import WebQQHandler
from ..webqqevents import BeforeLoginEvent

class BeforeLoginHandler(WebQQHandler):
    """ 登录之前的操作
    :接口返回
        ptuiCB('0','0','http://www.qq.com','0','登录成功!', 'qxbot');
    先检查是否需要验证码,不需要验证码则首先执行一次登录
    然后获取Cookie里的ptwebqq,skey保存在实例里,供后面的接口调用
    """
    def setup(self, password = None):
        assert password
        password = self.webqq.handle_pwd(password)
        params = [("u",self.webqq.qid), ("p",password),
                ("verifycode", self.webqq.check_code), ("webqq_type",10),
                ("remember_uin", 1),("login2qq",1),
                ("aid", self.webqq.aid), ("u1", "http://www.qq.com"),
                ("h", 1), ("ptredirect", 0), ("ptlang", 2052), ("from_ui", 1),
                ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                ("mibao_css","m_webqq"), ("t",1),
                ("g",1), ("js_type",0), ("js_ver", 10021)]
        url = "https://ssl.ptlogin2.qq.com/login"
        headers = {}
        if self.webqq.require_check:
            headers = {"Referer": "https://ui.ptlogin2.qq.com/cgi-"
                            "bin/login?target=self&style=5&mibao_css=m_"
                            "webqq&appid=1003903&enable_qlogin=0&no_ver"
                            "ifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Fl"
                            "oginproxy.html&f_url=loginerroralert&stron"
                            "g_login=1&login_state=10&t=20130221001"}
        self.make_http_sock(url, params, "GET", headers)


    def handle_read(self):
        self._readable = False
        resp = self.http_sock.make_response(self.sock, self.req, self.method)
        self.webqq.blogin_data = resp.read().decode("utf-8")
        self.webqq.event(BeforeLoginEvent(self.webqq.blogin_data, self))
        eval("self.webqq."+self.webqq.blogin_data.rstrip().rstrip(";"))

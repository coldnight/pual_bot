#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright 2013 cold
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/04 10:39:51
#   Desc    :   开启一个Server来处理验证码
#
import os
import time
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, asynchronous
try:
    from config import HTTP_LISTEN
except ImportError:
    HTTP_LISTEN = "127.0.0.1"

try:
    from config import HTTP_PORT
except ImportError:
    HTTP_PORT = 8000


class BaseHandler(RequestHandler):
    webqq = None
    r = None
    uin = None
    next_callback = None
    is_login = False



class CImgHandler(BaseHandler):
    def get(self):
        data = ""
        if os.path.exists(self.webqq.checkimg_path):
            with open(self.webqq.checkimg_path) as f:
                data = f.read()

        self.set_header("Content-Type", "image/jpeg")
        self.set_header("Content-Length", len(data))
        self.write(data)


class CheckHandler(BaseHandler):
    def get(self):
        path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            "check.jpg")
        if not os.path.exists(path):
            html = "暂不需要验证码"
        else:
            html = """
            <img src="/check" />
            <form action="/" method="POST">
                验证码:<input type="text" name="vertify" />
                <input type="submit" name="xx" value="提交" />
            </form>
            """
        self.write(html)

    @asynchronous
    def post(self):
        if not os.path.exists(self.webqq.checkimg_path) or\
           os.path.exists("lock"):
            self.write({"status":False, "message": u"暂不需要验证码"})
            return self.finish()

        code = self.get_argument("vertify")
        code = code.strip().lower().encode('utf-8')
        self.webqq.check_code = code
        pwd = self.webqq.handle_pwd(self.r, code.upper(), self.uin)
        self.next_callback(pwd, self.on_callback)

    def on_callback(self, status, msg = None):
        self.write({"status":status, "message":msg})
        self.finish()


class CheckImgAPIHandler(BaseHandler):
    is_exit = False
    def get(self):
        if os.path.exists("wait"):
            self.write({"status":False, "wait":True})
            return

        if os.path.exists("lock"):
            return self.write({"status":True, "require":False})

        if os.path.exists(self.webqq.checkimg_path):
            if self.webqq.require_check_time and \
            time.time() - self.webqq.require_check_time > 900:
                self.write({"status":False, "message":u"验证码过期"})
                self.is_exit = True
            else:
                url = "http://{0}/check".format(self.request.host)
                self.write({"status":True, "require":True, "url":url})
            return
        self.write({"status":True, "require":False})


    def on_connection_close(self):
        if self.is_exit:
            with open("wait", "w"):
                pass
            exit()


class SendMessageHandler(BaseHandler):
    @asynchronous
    def post(self):
        tomark = self.get_argument("markname")
        msg = self.get_argument("message")
        self.webqq.send_msg_with_markname(tomark, msg, self.on_back)

    def on_back(self, status, msg = None):
        self.write({"status":status, "message":msg})
        self.finish()



app = Application([(r'/', CheckHandler), (r'/check', CImgHandler),
                   (r'/api/check', CheckImgAPIHandler),
                   (r'/api/send', SendMessageHandler),
                   (r'/api/input', CheckHandler)
                   ])
app.listen(HTTP_PORT, address = HTTP_LISTEN)


def http_server_run(webqq):
    BaseHandler.webqq = webqq
    webqq.get_login_sig(BaseHandler)
    IOLoop.instance().start()


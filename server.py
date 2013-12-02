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
import logging
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

logger = logging.getLogger()

class BaseHandler(RequestHandler):
    webqq = None
    r = None
    uin = None
    is_login = False



class CImgHandler(BaseHandler):
    def get(self):
        data = ""
        if self.webqq.verify_img_path and os.path.exists(self.webqq.verify_img_path):
            with open(self.webqq.verify_img_path) as f:
                data = f.read()

        self.set_header("Content-Type", "image/jpeg")
        self.set_header("Content-Length", len(data))
        self.write(data)


class CheckHandler(BaseHandler):
    is_exit = False
    def get(self):
        if self.webqq.verify_img_path:
            path = self.webqq.verify_img_path
            if not os.path.exists(path):
                html = "暂不需要验证码"
            elif self.webqq.hub.is_wait():
                html = u"等待验证码"
            elif self.webqq.hub.is_lock():
                html = u"已经输入验证码, 等待验证"
            else:
                html = """
                <img src="/check" />
                <form action="/" method="POST">
                    验证码:<input type="text" name="vertify" />
                    <input type="submit" name="xx" value="提交" />
                </form>
                """
        else:
            html = "暂不需要验证码"
        self.write(html)

    @asynchronous
    def post(self):
        if (self.webqq.verify_img_path and
            not os.path.exists(self.webqq.verify_img_path)) or\
           self.webqq.hub.is_lock():
            self.write({"status":False, "message": u"暂不需要验证码"})
            return self.finish()

        code = self.get_argument("vertify")
        code = code.strip().lower().encode('utf-8')
        self.webqq.enter_verify_code(code, self.r, self.uin, self.on_callback)

    def on_callback(self, status, msg = None):
        self.write({"status":status, "message":msg})
        self.finish()

class CheckImgAPIHandler(BaseHandler):
    is_exit = False
    def get(self):
        if self.webqq.hub.is_wait():
            self.write({"status":False, "wait":True})
            return

        if self.webqq.hub.is_lock():
            return self.write({"status":True, "require":False})

        if self.webqq.verify_img_path and \
           os.path.exists(self.webqq.verify_img_path):
            if self.webqq.hub.require_check_time and \
            time.time() - self.webqq.hub.require_check_time > 900:
                self.write({"status":False, "message":u"验证码过期"})
                self.is_exit = True
            else:
                url = "http://{0}/check".format(self.request.host)
                self.write({"status":True, "require":True, "url":url})
            return
        self.write({"status":True, "require":False})


    def on_finish(self):
        if self.is_exit:
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
    webqq.run(BaseHandler)

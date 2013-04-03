#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   Wood.D Wong
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/03 10:55:18
#   Desc    :   工具类处理器
#
import json
from handlers.base import WebQQHandler

class RunPyCodeHandler(WebQQHandler):
    def setup(self, code = None, callback = None, pre= None):
        self.callback = callback
        self.pre = pre
        self.code = code
        url = "http://pythonec.appspot.com/run"
        params = [("code", code)]
        method = "POST"

        self.make_http_sock(url, params, method, {})

    def handle_write(self):
        super(RunPyCodeHandler, self).handle_write(code = self.code,
                                                   callback = self.callback)

    def handle_read(self):
        self._readable = False
        resp = self.make_http_resp()
        data = resp.read()
        import pdb;pdb.set_trace()
        try:
            result = json.loads(data)
            status = result.get("status")
            if status:
                content = u"OK: " + result.get("out")
            else:
                content = u"ERR: " + result.get("err")

            if self.pre:
                content = self.pre + content
        except ValueError:
            content = u"我出错了, 没办法执行, 我正在改"
        self.callback(content)
        self.remove_self()


class PasteCodeHandler(WebQQHandler):
    def setup(self, code = None, typ = "text", callback = None, pre = None):
        self.code = code
        self.typ = typ
        self.callback = callback
        self.pre = pre

        self.url = "http://paste.linuxzen.com"
        params = [("class", typ), ("code", code), ("paste", "ff")]
        method = "POST"

        self.make_http_sock(self.url, params, method, {})


    def handle_write(self):
        super(PasteCodeHandler, self).handle_write(code = self.code,
                                                   typ = self.typ,
                                                   callback = self.callback,
                                                   pre = self.pre)

    def handle_read(self):
        self._readable = False
        resp = self.make_http_resp()
        if resp.code == 302:
            url = resp.headers.get("Location")

        else:
            url = resp.url
        if url != self.url:
            self.callback(self.pre + url)

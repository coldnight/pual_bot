#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   Wood.D Wong
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/03 10:55:18
#   Desc    :   工具类处理器
#
import gzip
import json

from cStringIO import StringIO

from handlers.base import WebQQHandler

class RunPyCodeHandler(WebQQHandler):
    def setup(self, code = None, callback = None, pre= None):
        self.callback = callback
        self.pre = pre
        self.code = code
        url = "http://pythonec.appspot.com/run"
        #url = "http://localhost:8080/run"
        params = [("code", code.encode("utf-8"))]
        method = "POST"

        self.make_http_sock(url, params, method, {})

    def handle_write(self):
        super(RunPyCodeHandler, self).handle_write(code = self.code,
                                                   callback = self.callback)

    def handle_read(self):
        self._readable = False
        resp = self.make_http_resp()
        data = resp.read()
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
        params = [("class", typ), ("code", code.encode("utf-8")), ("paste", "ff")]
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
            content = url
            if self.pre: content = self.pre + content
            self.callback(content)


class CETranHandler(WebQQHandler):
    """ 英汉互译 """
    def setup(self, source = None, web = False, callback = None, pre = None):
        self.source = source
        self.callback = callback
        self.pre = pre
        self.web = web

        key = 1667350065
        keyfrom = "coldsblog"
        source = source.encode("utf-8")
        url = "http://fanyi.youdao.com/openapi.do"
        params = [("keyfrom", keyfrom), ("key", key),("type", "data"),
                  ("doctype", "json"), ("version",1.1), ("q", source)]
        method = "GET"
        headers = {"Accept-Language": "zh-CN,zh;q=0.8"}
        self.make_http_sock(url, params, method, headers)


    def handle_write(self):
        super(CETranHandler, self).handle_write(source = self.source,
                                                callback = self.callback,
                                                pre = self.pre)

    def handle_read(self):
        self._readable = False
        resp = self.make_http_resp()
        buf = StringIO(resp.read())
        with gzip.GzipFile(mode = "rb", fileobj = buf) as gf:
            data = gf.read()
        try:
            result = json.loads(data)
        except ValueError:
            body = u"error"
        else:
            errorCode = result.get("errorCode")
            if errorCode == 0:
                query = result.get("query")
                r = " ".join(result.get("translation"))
                basic = result.get("basic", {})
                body = u"{0}\n{1}".format(query, r)
                phonetic = basic.get("phonetic")
                if phonetic:
                    ps = phonetic.split(",")
                    if len(ps) == 2:
                        pstr = u"读音: 英 [{0}] 美 [{1}]".format(*ps)
                    else:
                        pstr = u"读音: {0}".format(*ps)
                    body += u"\n" + pstr

                exp = basic.get("explains")
                if exp:
                    body += u"\n其他释义:\n\t{0}".format(u"\n\t".join(exp))

                if self.web:
                    body += u"\n网络释义:\n"
                    web = result.get("web", [])
                    if web:
                        for w in web:
                            body += u"\t{0}\n".format(w.get("key"))
                            vs = u"\n\t\t".join(w.get("value"))
                            body += u"\t\t{0}\n".format(vs)

        if self.pre: body = self.pre + body
        self.callback(body)




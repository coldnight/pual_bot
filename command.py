#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/19 13:57:17
#   Desc    :   命令
#
import gzip
import json
from functools import partial
from cStringIO import StringIO

from http_stream import HTTPStream
from config import YOUDAO_KEY, YOUDAO_KEYFROM, MAX_LENGTH


class Command(object):
    http_stream = HTTPStream.instance()

    def py(self, code, callback):
        """ 执行Python代码
        Arguments:
            `code`      -   要执行的代码
            `callback`  -   发送消息的回调
        """
        url = "http://pythonec.appspot.com/run"
        #url = "http://localhost:8080/run"
        params = [("code", code.encode("utf-8"))]

        request = self.http_stream.make_post_request(url, params)
        read_py = partial(self.read_py, callback = callback)
        self.http_stream.add_request(request, read_py)

    def read_py(self, resp, callback):
        """ 读取执行Python代码的返回 """
        data = resp.read()
        try:
            result = json.loads(data)
            status = result.get("status")
            if status:
                content = u"OK: " + result.get("out")
            else:
                content = u"ERR: " + result.get("err")

        except ValueError:
            content = u"我出错了, 没办法执行, 我正在改"
        callback(content)

    def paste(self, code, callback, typ = "text"):
        """ 贴代码 """
        url = "http://paste.linuxzen.com"
        params = [("class", typ), ("code", code.encode("utf-8")), ("paste", "ff")]

        request = self.http_stream.make_post_request(url, params)
        read_back = partial(self.read_paste, oldurl = url, callback = callback)

        self.http_stream.add_request(request, read_back)


    def read_paste(self, resp, oldurl, callback):
        """ 读取贴代码结果, 并发送消息 """
        if resp.code == 302:
            url = resp.headers.get("Location")
        else:
            url = resp.url
        if url != oldurl:
            content = url
            callback(content)


    def cetr(self, source, callback,  web = False):
        """ 调用有道接口进行英汉互译 """
        key = YOUDAO_KEY
        keyfrom = YOUDAO_KEYFROM
        source = source.encode("utf-8")
        url = "http://fanyi.youdao.com/openapi.do"
        params = [("keyfrom", keyfrom), ("key", key),("type", "data"),
                  ("doctype", "json"), ("version",1.1), ("q", source)]

        request = self.http_stream.make_get_request(url, params)
        read_back = partial(self.read_cetr, callback = callback, web = web)
        self.http_stream.add_request(request, read_back)


    def read_cetr(self, resp, callback, web):
        """ 读取英汉翻译的结果 """
        source = resp.read()
        try:
            buf = StringIO(source)
            with gzip.GzipFile(mode = "rb", fileobj = buf) as gf:
                data = gf.read()
        except:
            data = source

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

                if web:
                    body += u"\n网络释义:\n"
                    web = result.get("web", [])
                    if web:
                        for w in web:
                            body += u"\t{0}\n".format(w.get("key"))
                            vs = u"\n\t\t".join(w.get("value"))
                            body += u"\t\t{0}\n".format(vs)

        callback(body)

    def send_msg(self, msg, callback, nick = None):
        if len(msg) <= MAX_LENGTH:
            body = nick + msg if nick else msg
            callback(body)
        else:
            self.paste(msg, callback, nick)

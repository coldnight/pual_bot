#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/19 13:57:17
#   Desc    :   命令
#
import re
import gzip
import json
import urllib2
import httplib
import logging
from functools import partial
from cStringIO import StringIO
from lxml import etree

from http_stream import HTTPStream, Form
from config import YOUDAO_KEY, YOUDAO_KEYFROM, MAX_LENGTH, SimSimi_Proxy


def upload_file(filename, path):
    """ 上传文件
    - `path`      文件路径
    """
    form = Form()
    filename = filename.encode("utf-8")
    form.add_file(fieldname='img', filename=filename,
                    fileHandle=open(path))
    req = urllib2.Request("http://paste.linuxzen.com")
    req.add_header("Content-Type", form.get_content_type())
    req.add_header("Content-Length", len(str(form)))
    req.add_data(str(form))
    return urllib2.urlopen(req)


class Command(object):
    http_stream = HTTPStream.instance()
    _sim_try = {}
    simsimi_proxy = False

    def url_info(self, url, callback, isredirect = False):
        """ 获取url信息
        Arguments:
            `url`   -   链接
            `callback`  -   发送消息的回调
            `isredirect` -   是否是重定向
        """
        request = self.http_stream.make_get_request(url)
        _url_info = partial(self._url_info, callback = callback, url = url,
                            isredirect = isredirect)
        _eurl_info = partial(self._eurl_info, callback = callback, url = url)
        self.http_stream.add_request(request, _url_info, _eurl_info)


    def _url_info(self, resp, callback, url, isredirect = False):
        """ 读取url_info的回调 """
        meta_charset = re.compile(br'<meta\s+http-equiv="?content-type"?'
                                  '\s+content="?[^;]+;\s*charset=([^">]+'
                                  ')"?\s*/?>|<meta\s+charset="?([^">/"]+'
                                  ')"?\s*/?>', re.IGNORECASE)
        body = ""
        content = resp.read()
        c_type =  resp.headers.get("Context-Type", "text/html")
        if resp.code in [200]:
            if c_type == "text/html":
                charset = meta_charset.findall(content)
                logging.info("Found charset {0!r} in url {1}".format(charset, url))
                if len(charset) == 1 and len(charset[0]) == 2:
                    charset = charset[0][0] if charset[0][0] else charset[0][1]
                else:
                    charset = ""

                if charset.lower().strip() == "gb2312":
                    charset = "gbk"

                if charset:
                    ucont = content.lower().decode(charset).encode("utf-8").decode("utf-8")
                else:
                    ucont = content.lower().decode("utf-8")
                parser = etree.HTML(ucont)
                title = parser.xpath(u"//title")
                title = title[0].text if len(title) >= 1 else None
                if title:
                    body += u"网页标题: "+title.replace("\r", "").replace("\n", "")
                if isredirect:
                    body += u"(重定向到:{0})".format(url)
        elif resp.code in [302, 301]:
            dst = resp.headers.get("Location")
            self.url_info(dst, callback, True)
        else:
            body = u"({0} {1} {2})".format(url, resp.code,
                                         httplib.responses[resp.code])

        if body:
            callback(body)


    def _eurl_info(self, errcode, errmsg, url, callback):
        """ 处理url_info错误 """
        body = u"({0} {1})".format(url, errmsg)
        callback(body)


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


    def shell(self, session, statement, callback):
        """ 实现Python Shell
        Arguments:
            `session`   -   区别用户的shell
            `statement` -   Python语句
            `callback`  -   发送结果的回调
        """
        if statement.strip() in ["cls", "clear"]:
            url = "http://pythonec.appspot.com/drop"
            params = [("session", session),]
        else:
            url = "http://pythonec.appspot.com/shell"
            #url = "http://localhost:8080/shell"
            params = [("session", session),
                    ("statement", statement.encode("utf-8"))]
        request = self.http_stream.make_get_request(url, params)

        def read_shell(resp, callback):
            data = resp.read()
            if not data:
                data = "OK"
            callback(data.decode("utf-8"))
            return
        self.http_stream.add_request(request,
                                     partial(read_shell, callback = callback))


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


    def simsimi(self, content, callback):
        """ simsimi 小黄鸡 """
        msg_url = "http://www.simsimi.com/func/req"
        msg_params = (("msg", content.encode("utf-8")), ("lc", "ch"))
        request = self.http_stream.make_get_request(msg_url, msg_params)
        request.add_header("Referer", "http://www.simsimi.com/talk.htm?lc=ch")
        request.add_header("X-Requested-With", "XMLHttpRequest")

        def read_simsimi(resp):
            result = resp.read()
            if result:
                try:
                    response = json.loads(result)
                    res = response.get("response")
                    if not res or (res and res.startswith("Unauthorized access!.")):
                        if not self._sim_try.has_key(content):
                            self._sim_try[content] = 0
                        if self._sim_try.get(content) < 10:
                            logging.warn("SimSimi error with response {0}".format(res))
                            if not self.simsimi_proxy and self._sim_try[content] > 1:
                                self.simsimi_proxy = True
                            self._sim_try[content] += 1
                            self.simsimi(content, callback)
                        else:
                            self._sim_try[content] = 0
                            callback(u"T^T ip被SimSimi封了, 无法应答")
                        return

                    self._sim_try[content] = 0
                    callback(response.get("response"))
                except ValueError:
                    logging.warn("SimSimi error with response {0}".format(result))
                    self.simsimi(content, callback)

        if self.simsimi_proxy:
            self.http_stream.add_request(request, read_simsimi, proxy=SimSimi_Proxy)
        else:
            self.http_stream.add_request(request, read_simsimi)


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
        body = None
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

            if errorCode == 50:
                body = u"无效的有道key"

        if not body:
            body = u"没有结果"

        callback(body)

    def send_msg(self, msg, callback, nick = None):
        if len(msg) <= MAX_LENGTH:
            body = nick + msg if nick else msg
            callback(body)
        else:
            callback = partial(self.send_msg, callback = callback, nick = nick)
            self.paste(msg, callback)

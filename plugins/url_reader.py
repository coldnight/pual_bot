#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:00:06
#   Desc    :   读取URL信息(标题)插件
#
import re
import httplib

from functools import partial

from plugins import BasePlugin


class UrlReader(object):
    def __init__(self, http, logger):
        self.http = http
        self.logger = logger

    def read(self, url, callback, isredirect = False):
        callback = partial(self._read, callback = callback, url = url,
                           isredirect = isredirect)
        self.http.get(url, callback = callback)

    def _read(self, resp, callback, url, isredirect = False):
        meta_charset = re.compile(br'<meta\s+http-equiv="?content-type"?'
                                  '\s+content="?[^;]+;\s*charset=([^">]+'
                                  ')"?\s*/?>|<meta\s+charset="?([^">/"]+'
                                  ')"?\s*/?>', re.IGNORECASE)
        body = ""
        content = resp.body
        c_type =  resp.headers.get("Context-Type", "text/html")
        if resp.code in [200]:
            if c_type == "text/html":
                charset = meta_charset.findall(content)
                self.logger.info("Found charset {0!r} in url {1}".format(charset, url))
                if len(charset) == 1 and len(charset[0]) == 2:
                    charset = charset[0][0] if charset[0][0] else charset[0][1]
                else:
                    charset = ""

                if charset.lower().strip() == "gb2312":
                    charset = "gbk"

                if charset:
                    ucont = content.decode(charset).encode("utf-8").decode("utf-8")
                else:
                    ucont = content.decode("utf-8")
                titles = self._TITLE_PATTERN.findall(ucont)
                title = titles[0] if titles else None
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


class URLReaderPlugin(BasePlugin):
    URL_RE = re.compile(r"(http[s]?://(?:[-a-zA-Z0-9_]+\.)+[a-zA-Z]+(?::\d+)"
                        "?(?:/[-a-zA-Z0-9_%./]+)*\??[-a-zA-Z0-9_&%=.]*)",
                        re.UNICODE)

    def is_match(self, from_uin, content, type):
        urls = self.URL_RE.findall(content)
        if urls:
            self._urls = urls
            self._reader = UrlReader(self.http, self.logger)
            return True
        return False

    def handle_message(self, callback):
        [self._reader.read(url, callback) for url in self._urls]

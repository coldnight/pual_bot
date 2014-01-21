#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:00:06
#   Desc    :   读取URL信息(标题)插件
#
import re

from plugins import BasePlugin

from _linktitle import get_urls, fetchtitle

class URLReaderPlugin(BasePlugin):
    URL_RE = re.compile(r"(http[s]?://(?:[-a-zA-Z0-9_]+\.)+[a-zA-Z]+(?::\d+)"
                        "?(?:/[-a-zA-Z0-9_%./]+)*\??[-a-zA-Z0-9_&%=.]*)",
                        re.UNICODE)

    def is_match(self, from_uin, content, type):
        urls = get_urls(content)
        if urls:
            self._urls = urls
            return True
        return False

    def handle_message(self, callback):
        fetchtitle(self._urls, callback)

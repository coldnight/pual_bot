#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:23:34
#   Desc    :   翻译插件
#
import json
import traceback

import config

from plugins import BasePlugin

class TranslatePlugin(BasePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith("-tr"):
            web = content.startswith("-trw")
            self.is_web = web
            self.body = content.lstrip("-trw" if web else "-tr").strip()
            return True
        return False

    def handle_message(self, callback):
        key = config.YOUDAO_KEY
        keyfrom = config.YOUDAO_KEYFROM
        source = self.body.encode("utf-8")
        url = "http://fanyi.youdao.com/openapi.do"
        params = [("keyfrom", keyfrom), ("key", key),("type", "data"),
                  ("doctype", "json"), ("version",1.1), ("q", source)]
        self.http.get(url, params, callback = self.read_result,
                      kwargs = {"callback":callback})

    def read_result(self, resp, callback):
        web = self.is_web
        try:
            result = json.loads(resp.body)
        except ValueError:
            self.logger.warn(traceback.format_exc())
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

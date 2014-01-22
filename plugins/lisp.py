#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/22 14:13:23
#   Desc    :   调用接口实现运行Lisp程序
#
import re
import logging

from plugins import BasePlugin

logger = logging.getLogger("plugin")

class LispPlugin(BasePlugin):
    url = "http://www.compileonline.com/execute_new.php"
    result_p = re.compile(r'<pre>(.*?)</pre>', flags = re.U|re.M|re.S)

    def is_match(self, from_uin, content, type):
        if content.startswith("(") and content.endswith(")"):
            self._code = content
            return True
        return False

    def handle_message(self, callback):
        params = {"args":"", "code":self._code.encode("utf-8"),
                  "inputs":"", "lang":"lisp", "stdinput":""}
        def read(resp):
            logger.info(u"Lisp request success, result: {0}".format(resp.body))
            result = self.result_p.findall(resp.body)
            result = "" if not result else result[0]
            callback(result)
        self.http.post(self.url, params, callback = read)

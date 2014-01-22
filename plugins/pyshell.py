#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:29:39
#   Desc    :   Python 在线 Shell 插件
#
import config

from plugins.paste import PastePlugin

class PythonShellPlugin(PastePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith(">>>"):
            body = content.lstrip(">").lstrip(" ")
            bodys = []
            for b in body.replace("\r\n", "\n").split("\n"):
                bodys.append(b.lstrip(">>>"))
            self.body = "\n".join(bodys)
            self.from_uin = from_uin
            return True
        return False

    def handle_message(self, callback):
        self.shell(callback)

    def shell(self, callback):
        """ 实现Python Shell
        Arguments:
            `callback`  -   发送结果的回调
        """
        if self.body.strip() in ["cls", "clear"]:
            url = "http://pythonec.appspot.com/drop"
            params = [("session", self.from_uin),]
        else:
            url = "http://pythonec.appspot.com/shell"
            #url = "http://localhost:8080/shell"
            params = [("session", self.from_uin),
                    ("statement", self.body.encode("utf-8"))]

        def read_shell(resp):
            data = resp.body
            if not data:
                data = "OK"
            if len(data) > config.MAX_LENGTH:
                return self.paste(data, callback, "")

            if data.count("\n") > 10:
                data.replace("\n", " ")

            callback(data.decode("utf-8"))
            return

        self.http.get(url, params, callback = read_shell)

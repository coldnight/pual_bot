#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:18:53
#   Desc    :   相应基本命令插件
#
import time

from datetime import datetime

from plugins import BasePlugin


class CommandPlugin(BasePlugin):
    def uptime(self):
        up_time = datetime.fromtimestamp(self.webqq.start_time)\
                .strftime("%H:%M:%S")
        now = time.time()

        sub = int(now - self.start_time)
        num, unit, oth = None, None, ""
        if sub < 60:
            num, unit = sub, "sec"
        elif sub > 60 and sub < 3600:
            num, unit = sub / 60, "min"
        elif sub > 3600 and sub < 86400:
            num = sub / 3600
            unit = ""
            num = "{0}:{1}".format("%02d" % num,
                                   ((sub - (num * 3600)) / 60))
        elif sub > 86400:
            num, unit = sub / 84600, "days"
            h = (sub - (num * 86400)) / 3600
            m = (sub - ((num * 86400) + h * 3600)) / 60
            if h or m:
                oth = ", {0}:{1}".format(h, m)

        return "{0} up {1} {2} {3}, handled {4} message(s)"\
                .format(up_time, num, unit, oth, self.webqq.msg_num)


    def is_match(self, from_uin, content, type):
        ABOUT_STR = u"\nAuthor    :   cold\nE-mail    :   wh_linux@126.com\n"\
                u"HomePage  :   http://t.cn/zTocACq\n"\
                u"Project@  :   http://git.io/hWy9nQ"
        HELP_DOC = u"http://p.vim-cn.com/cbc2/"
        ping_cmd = "ping"
        about_cmd = "about"
        help_cmd = "help"
        commands = [ping_cmd, about_cmd, help_cmd, "uptime"]
        command_resp = {ping_cmd:u"小的在", about_cmd:ABOUT_STR,
                        help_cmd:HELP_DOC,
                        "uptime":self.uptime}

        if content.encode("utf-8").strip().lower() in commands:
            body = command_resp[content.encode("utf-8").strip().lower()]
            if not isinstance(body, (str, unicode)):
                body = body()
            self.body = body
            return True

    def handle_message(self, callback):
        callback(self.body)

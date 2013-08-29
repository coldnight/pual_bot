#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright 2013 cold
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 11:44:05
#   Desc    :   消息调度
#
import re
import logging
from functools import partial

from command import Command
from config import MAX_RECEIVER_LENGTH


code_typs = ['actionscript', 'ada', 'apache', 'bash', 'c', 'c#', 'cpp',
              'css', 'django', 'erlang', 'go', 'html', 'java', 'javascript',
              'jsp', 'lighttpd', 'lua', 'matlab', 'mysql', 'nginx',
              'objectivec', 'perl', 'php', 'python', 'python3', 'ruby',
              'scheme', 'smalltalk', 'smarty', 'sql', 'sqlite3', 'squid',
              'tcl', 'text', 'vb.net', 'vim', 'xml', 'yaml']

ABOUT_STR = u"\nAuthor    :   cold\nE-mail    :   wh_linux@126.com\n"\
        u"HomePage  :   http://t.cn/zTocACq\n"\
        u"Project@  :   http://git.io/hWy9nQ"

HELP_DOC = u"http://p.vim-cn.com/cbc2/"
u"""-tr <content>       可以对<content>进行英汉互译
```<type>\\n<code>  可以将<code>以<type>高亮的方式贴代码
>>> <statement>     可以执行Python语句
ping                可以查看是否在线
about               可以查看相关信息
help                显示本信息
"""


URL_RE = re.compile(r"(http[s]?://(?:[-a-zA-Z0-9_]+\.)+[a-zA-Z]+(?::\d+)"
                    "?(?:/[-a-zA-Z0-9_%./]+)*\??[-a-zA-Z0-9_&%=.]*)",
                    re.UNICODE)

class MessageDispatch(object):
    """ 消息调度器 """
    def __init__(self, webqq):
        self.webqq = webqq
        self.cmd = Command()

    def send_msg(self, content, callback, nick = None):
        self.cmd.send_msg(content, callback, nick)

    def handle_qq_msg_contents(self, contents):
        content = ""
        for row in contents:
            if isinstance(row, (str, unicode)):
                content += row.replace(u"【提示：此用户正在使用Q+"
                                       u" Web：http://web.qq.com/】", "")\
                        .replace(u"【提示：此用户正在使用Q+"
                                       u" Web：http://web3.qq.com/】", "")
        return  content.replace("\r", "\n").replace("\r\n", "\n")\
                .replace("\n\n", "\n")


    def handle_qq_group_msg(self, message):
        """ 处理组消息 """
        value = message.get("value", {})
        gcode = value.get("group_code")
        uin = value.get("send_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(contents)
        uname = self.webqq.get_group_member_nick(gcode, uin)
        if content:
            logging.info(u"从 {1} 获取群消息 {0}".format(content, gcode))
            pre = u"{0}: ".format(uname)
            callback = partial(self.webqq.send_group_msg, gcode)
            self.handle_content(uin, content, callback, "g", pre)


    def handle_qq_message(self, message, is_sess = False):
        """ 处理QQ好友消息 """
        value = message.get("value", {})
        from_uin = value.get("from_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(contents)
        if content:
            typ = "Sess" if is_sess else "Friend"
            logging.info(u"获取来自 {2} 类型位 {0} 的消息:  {1}"
                         .format(typ, content, from_uin))
            callback = self.webqq.send_sess_msg if is_sess else self.webqq.send_buddy_msg
            callback = partial(callback, from_uin)
            self.handle_content(from_uin, content, callback, "b")


    def handle_content(self, from_uin, content, callback, typ = "g", pre = None):
        """ 处理内容
        Arguments:
            `from_uin`  -       发送者uin
            `content`   -       内容
            `callback`  -       仅仅接受内容参数的回调
            `typ`       -       消息类型 g 群消息  b 好友消息
            `pre`       -       处理后内容前缀
        """
        send_msg = partial(self.send_msg, callback = callback, nick = pre)
        content = content.strip()

        urls = URL_RE.findall(content)
        if urls:
            logging.info(u"从 {1} 中获取链接: {0!r}".format(urls, content))
            for url in urls:
                self.cmd.url_info(url, send_msg)

        if content.startswith("-py"):
            body = content.lstrip("-py").strip()
            self.cmd.py(body, send_msg)
            return

        if content.startswith("```"):
            typ = content.split("\n")[0].lstrip("`").strip().lower()
            if typ not in code_typs: typ = "text"
            code = "\n".join(content.split("\n")[1:])
            self.cmd.paste(code, send_msg, typ)
            return

        ping_cmd = "ping"
        about_cmd = "about"
        uptime_cmd = "uptime"
        help_cmd = "help"
        commands = [ping_cmd, about_cmd, help_cmd, uptime_cmd]
        command_resp = {ping_cmd:u"小的在", about_cmd:ABOUT_STR,
                        help_cmd:HELP_DOC, uptime_cmd : self.webqq.get_uptime()}

        if content.encode("utf-8").strip().lower() in commands:
            body = command_resp[content.encode("utf-8").strip().lower()]
            if not isinstance(body, (str, unicode)):
                body = body()
            send_msg(body)
            return

        if content.startswith("-tr"):
            if content.startswith("-trw"):
                web = True
                st = "-trw"
            else:
                web = False
                st = "-tr"
            body = content.lstrip(st).strip()
            self.cmd.cetr(body, send_msg, web)
            return

        if content.startswith(">>>"):
            body = content.lstrip(">").lstrip(" ")
            self.cmd.shell(from_uin, body, send_msg)
            return

        if typ == "b":
            if content.startswith(u"设置签名:") and content.count("|") == 1:
                password, signature = content.strip(u"设置签名:").split("|")
                self.webqq.set_signature(signature, password, send_msg)
                return

            if content:
                self.cmd.talk(content, send_msg)
            return

        nickname = self.webqq.nickname.decode('utf-8').lower()
        if content.lower().startswith(nickname) \
           or content.lower().endswith(nickname):
            content = content.lower().strip(nickname).strip()
            if content:
                self.cmd.talk(content, send_msg)
            return




        if u"提问的智慧" in content:
            bodys = []
            bodys.append(u"提问的智慧:")
            bodys.append(u"原文: http://t.cn/hthAh")
            bodys.append(u"译文: http://t.cn/SUHbCJ")
            bodys.append(u"简化版: http://t.cn/hI2oe")
            bodys.append(u"概括:")
            bodys.append(u"1. 详细描述问题: 目的, 代码, 错误信息等")
            bodys.append(u"2. 代码不要直接发到QQ上, 以免被替换成表情或丢失缩进")
            bodys.append(u"3. 向帮你解决问题的人说谢谢 ")
            callback("\n".join(bodys))



        if len(content) > MAX_RECEIVER_LENGTH:
            if pre:
                cpre = u"{0}内容过长: ".format(pre)
            else:
                cpre = pre
            send_pre_msg = partial(self.send_msg, callback = callback, nick = cpre)
            self.cmd.paste(content, send_pre_msg)


    def dispatch(self, qq_source):
        if qq_source.get("retcode") == 0:
            messages = qq_source.get("result")
            for m in messages:
                if m.get("poll_type") == "group_message":
                    self.handle_qq_group_msg(m)
                if m.get("poll_type") == "message":
                    self.handle_qq_message(m)
                if m.get("poll_type") == "kick_message":
                    self.webqq.stop()
                if m.get("poll_type") == "sess_message":
                    self.handle_qq_message(m, True)

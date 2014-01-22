#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:13:09
#   Desc    :   粘贴代码插件
#
from plugins import BasePlugin

class PastePlugin(BasePlugin):
    code_typs = ['actionscript', 'ada', 'apache', 'bash', 'c', 'c#', 'cpp',
            'css', 'django', 'erlang', 'go', 'html', 'java', 'javascript',
            'jsp', 'lighttpd', 'lua', 'matlab', 'mysql', 'nginx',
            'objectivec', 'perl', 'php', 'python', 'python3', 'ruby',
            'scheme', 'smalltalk', 'smarty', 'sql', 'sqlite3', 'squid',
            'tcl', 'text', 'vb.net', 'vim', 'xml', 'yaml']

    def is_match(self, from_uin, content, type):
        if content.startswith("```"):
            typ = content.split("\n")[0].lstrip("`").strip().lower()
            self.ctype =  typ if typ in self.code_typs else "text"
            self.code = "\n".join(content.split("\n")[1:])
            return True
        return False

    def paste(self, code, callback, ctype = "text"):
        """ 贴代码 """
        params = {'vimcn':code.encode("utf-8")}
        url = "http://p.vim-cn.com/"

        self.http.post(url, params, callback = self.read_paste,
                       kwargs = {"callback":callback, "ctype":ctype})


    def read_paste(self, resp, callback, ctype="text"):
        """ 读取贴代码结果, 并发送消息 """
        if resp.code == 200:
            content = resp.body.strip().rstrip("/") + "/" + ctype
        elif resp.code == 400:
            content = u"内容太短, 不需要贴!"
        else:
            content = u"没贴上, 我也不知道为什么!"

        callback(content)


    def handle_message(self, callback):
        self.paste(self.code, callback, self.ctype)

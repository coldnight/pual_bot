#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/01 11:44:05
#   Desc    :   消息调度
#
from functools import partial
from utils import get_logger

from utilhandlers import RunPyCodeHandler, PasteCodeHandler

code_typs = ['actionscript', 'ada', 'apache', 'bash', 'c', 'c#', 'cpp',
              'css', 'django', 'erlang', 'go', 'html', 'java', 'javascript',
              'jsp', 'lighttpd', 'lua', 'matlab', 'mysql', 'nginx',
              'objectivec', 'perl', 'php', 'python', 'python3', 'ruby',
              'scheme', 'smalltalk', 'smarty', 'sql', 'sqlite3', 'squid',
              'tcl', 'text', 'vb.net', 'vim', 'xml', 'yaml']

class MessageDispatch(object):
    """ 消息调度器 """
    def __init__(self, webqq):
        self.logger = get_logger()
        self.webqq = webqq
        self.uin_qid_map = {}          # uin 到QQ号的映射
        self.qid_uin_map = {}          # QQ号到uin的映射
        self._maped = False

    def get_map(self):
        uins = [key for key, value in self.webqq.group_map.items()]
        for uin in uins:
            qid = self.get_qid_with_uin(uin)
            self.uin_qid_map[uin] = qid
            self.qid_uin_map[qid] = uin
        self._maped = True


    def get_uin_account(self, xmpp):
        """ 根据xmpp帐号获取桥接的qq号的uin """
        qids = []
        for qid, x in self.bridges:
            if x == xmpp:
                qids.append(self.qid_uin_map.get(qid))

        return qids

    def get_qid_with_uin(self, uin):
        qid = self.uin_qid_map.get(uin)
        if not qid:
            qid = self.webqq.get_qid_with_uin(uin)
            self.uin_qid_map[uin] = qid
        return qid

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
            pre = u"{0}: ".format(uname)
            callback = partial(self.webqq.send_group_msg, gcode)
            self.handle_content(content, callback, pre)


    def handle_qq_message(self, message):
        """ 处理QQ好友消息 """
        value = message.get("value", {})
        from_uin = value.get("from_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(contents)
        if content:
            callback = partial(self.webqq.send_buddy_msg, from_uin)
            self.handle_content(content, callback)

    def handle_content(self, content, callback, pre = None):
        """ 处理内容
        Arguments:
            `content`   -       内容
            `callback`  -       仅仅接受内容参数的回调
            `pre`       -       处理后内容前缀
        """
        if content.startswith("-"):
            cmd, body = content.split(" ")[0].lstrip("-"),\
                    content.lstrip("-py").strip()
            if cmd == "py":
                handler = RunPyCodeHandler(self.webqq, code = body,
                                           callback = callback, pre = pre)
                self.webqq.mainloop.add_handler(handler)

        if content.startswith("```"):
            typ = content.split("\n")[0].lstrip("`").strip().lower()
            if typ not in code_typs: typ = "text"
            code = "\n".join(content.split("\n")[1:])
            handler = PasteCodeHandler(self.webqq, code=code, typ=typ,
                                       callback=callback, pre=pre)
            self.webqq.mainloop.add_handler(handler)

    def dispatch(self, qq_source):
        if qq_source.get("retcode") == 0:
            messages = qq_source.get("result")
            for m in messages:
                if m.get("poll_type") == "group_message":
                    self.handle_qq_group_msg(m)
                if m.get("poll_type") == "message":
                    self.handle_qq_message(m)

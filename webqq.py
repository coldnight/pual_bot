#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/14 13:23:49
#   Desc    :
#
from __future__ import print_function

import re
import os
import sys
import config
import atexit
import logging

from functools import partial


from twqq.client import WebQQClient
from twqq.requests import kick_message_handler, PollMessageRequest
from twqq.requests import system_message_handler, group_message_handler
from twqq.requests import buddy_message_handler, BeforeLoginRequest
from twqq.requests import register_request_handler, BuddyMsgRequest

from server import http_server_run
from _simsimi import SimSimiTalk
from command import Command


logger = logging.getLogger("client")

class Client(WebQQClient):
    verify_img_path = None
    message_requests = {}
    simsimi = SimSimiTalk()
    command = Command()

    URL_RE = re.compile(r"(http[s]?://(?:[-a-zA-Z0-9_]+\.)+[a-zA-Z]+(?::\d+)"
                        "?(?:/[-a-zA-Z0-9_%./]+)*\??[-a-zA-Z0-9_&%=.]*)",
                        re.UNICODE)

    def handle_verify_code(self, path, r, uin):
        self.verify_img_path = path

        if getattr(config, "UPLOAD_CHECKIMG", False):
            logger.info(u"正在上传验证码...")
            res = self.hub.upload_file("check.jpg", self.hub.checkimg_path)
            logger.info(u"验证码已上传, 地址为: {0}".format(res.read()))

        if getattr(config, "HTTP_CHECKIMG", False):
            if hasattr(self, "handler") and self.handler:
                self.handler.r = r
                self.handler.uin = uin

            logger.info("请打开 http://{0}:{1} 输入验证码"
                        .format(config.HTTP_LISTEN, config.HTTP_PORT))
        else:
            logger.info(u"验证码本地路径为: {0}".format(self.hub.checkimg_path))
            check_code = None
            while not check_code:
                check_code = raw_input("输入验证码: ")
            self.enter_verify_code(check_code, r, uin)


    def enter_verify_code(self, code, r, uin, callback = None):
        super(Client, self).enter_verify_code(code, r, uin)
        self.verify_callback = callback


    @register_request_handler(BeforeLoginRequest)
    def handle_verify_check(self, request, resp, data):
        if hasattr(self, "verify_callback") and callable(self.verify_callback):
            if not data:
                self.verify_callback(False, "没有数据返回验证失败, 尝试重新登录")
                return

            args = request.get_back_args(data)
            scode = int(args[0])
            if scode == 0:
                self.verify_callback(True)
            else:
                self.verify_callback(False, args[4])


    @kick_message_handler
    def handle_kick(self, message):
        sys.exit()    # 退出重启


    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == "verify_required":
            self.hub.accept_verify(from_uin, account, str(account))

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        callback = partial(self.send_group_with_nick, member_nick, group_code)
        self.handle_message(send_uin, content, callback)


    def _handle_content_url(self, content, callback):
        urls = self.URL_RE.findall(content)
        if urls:
            logging.info(u"从 {1} 中获取链接: {0!r}".format(urls, content))
            for url in urls:
                self.command.url_info(url, callback)
            return True

    def _paste_content(self, content, callback):
        code_typs = ['actionscript', 'ada', 'apache', 'bash', 'c', 'c#', 'cpp',
              'css', 'django', 'erlang', 'go', 'html', 'java', 'javascript',
              'jsp', 'lighttpd', 'lua', 'matlab', 'mysql', 'nginx',
              'objectivec', 'perl', 'php', 'python', 'python3', 'ruby',
              'scheme', 'smalltalk', 'smarty', 'sql', 'sqlite3', 'squid',
              'tcl', 'text', 'vb.net', 'vim', 'xml', 'yaml']

        if content.startswith("```"):
            typ = content.split("\n")[0].lstrip("`").strip().lower()
            if typ not in code_typs: typ = "text"
            code = "\n".join(content.split("\n")[1:])
            self.command.paste(code, callback, typ)
            return True


    def _handle_command(self, content, callback):
        ABOUT_STR = u"\nAuthor    :   cold\nE-mail    :   wh_linux@126.com\n"\
                u"HomePage  :   http://t.cn/zTocACq\n"\
                u"Project@  :   http://git.io/hWy9nQ"
        HELP_DOC = u"http://p.vim-cn.com/cbc2/"
        ping_cmd = "ping"
        about_cmd = "about"
        help_cmd = "help"
        commands = [ping_cmd, about_cmd, help_cmd]
        command_resp = {ping_cmd:u"小的在", about_cmd:ABOUT_STR,
                        help_cmd:HELP_DOC}

        if content.encode("utf-8").strip().lower() in commands:
            body = command_resp[content.encode("utf-8").strip().lower()]
            if not isinstance(body, (str, unicode)):
                body = body()
            callback(body)
            return True


    def handle_message(self, from_uin, content, callback, type="g"):
        content = content.strip()
        if self._handle_content_url(content, callback):
            return

        if self._paste_content(content, callback):
            return

        if self._handle_command(content, callback):
            return

        if self._handle_trans(content, callback):
            return

        if self._handle_run_code(from_uin, content, callback):
            return

        self._handle_simsimi(content, callback, type)


    def _handle_trans(self, content, callback):
        if content.startswith("-tr"):
            if content.startswith("-trw"):
                web = True
                st = "-trw"
            else:
                web = False
                st = "-tr"
            body = content.lstrip(st).strip()
            self.command.cetr(body, callback, web)
            return True

    def _handle_run_code(self, from_uin, content, callback):
        if content.startswith(">>>"):
            body = content.lstrip(">").lstrip(" ")
            bodys = []
            for b in body.replace("\r\n", "\n").split("\n"):
                bodys.append(b.lstrip(">>>"))
            body = "\n".join(bodys)
            self.command.shell(from_uin, body, callback)
            return True

    def _handle_simsimi(self, content, callback, typ):
        if typ == "g":
            if content.startswith(self.hub.nickname.lower().strip()) or \
               content.endswith(self.hub.nickname.lower().strip()):
                self.simsimi.talk(content.strip(self.hub.nickname), callback)
        else:
            self.simsimi.talk(content.strip(self.hub.nickname), callback)


    def send_group_with_nick(self, nick, group_code, content):
        content = u"{0}: {1}".format(nick, content)
        self.hub.send_group_msg(group_code, content)

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        callback = partial(self.hub.send_buddy_msg, from_uin)
        self.handle_message(from_uin, content, callback, 'b')


    @register_request_handler(PollMessageRequest)
    def handle_qq_errcode(self, request, resp, data):
        if data and data.get("retcode") in [121, 100006]:
            logger.error(u"获取登出消息 {0!r}".format(data))
            exit()


    def send_msg_with_markname(self, markname, message, callback = None):
        request = self.hub.send_msg_with_markname(markname, message)
        if request is None:
            callback(False, u"不存在该好友")

        self.message_requests[request] = callback

    @register_request_handler(BuddyMsgRequest)
    def markname_message_callback(self, request, resp, data):
        callback = self.message_requests.get(request)
        if not callback:
            return

        if not data:
            callback(False, u"服务端没有数据返回")
            return

        if data.get("retcode") != 0:
            callback(False, u"发送失败, 错误代码:".format(data.get("retcode")))
            return

        callback(True)


    def run(self, handler = None):
        self.handler = handler
        super(Client, self).run()




def run_daemon(callback, args = (), kwargs = {}):
    path = os.path.abspath(os.path.dirname(__file__))
    def _fork(num):
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #%d faild:%d(%s)\n" % (num, e.errno,
                                                          e.strerror))
            sys.exit(1)


    _fork(1)

    os.setsid()
    # os.chdir("/")
    os.umask(0)

    _fork(2)
    pp = os.path.join(path, "pid.pid")

    with open(pp, 'w') as f:
        f.write(str(os.getpid()))

    lp = os.path.join(path, "log.log")
    lf = open(lp, 'a')
    os.dup2(lf.fileno(), sys.stdout.fileno())
    os.dup2(lf.fileno(), sys.stderr.fileno())
    callback(*args, **kwargs)

    def _exit():
        os.remove(pp)
        lf.close()

    atexit.register(_exit)


def main():
    webqq = Client(config.QQ, config.QQ_PWD)
    try:
        if getattr(config, "HTTP_CHECKIMG", False):
            http_server_run(webqq)
        else:
            webqq.run()
    except KeyboardInterrupt:
        print("Exiting...", file =  sys.stderr)
    except SystemExit:
        os.execv(sys.executable, [sys.executable] + sys.argv)



if __name__ == "__main__":
    from logging.handlers import RotatingFileHandler
    for name in ["twqq", "client"]:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG if config.DEBUG else logging.NOTSET)
        if not config.DEBUG:
            file_handler = RotatingFileHandler(
                getattr(config, "LOG_PATH", "log.log"),
                maxBytes = getattr(config, "LOG_MAX_SIZE", 5 * 1024 * 1024),
                backupCount = getattr(config, "LOG_BACKUPCOUNT", 10)
            )
            logger.addHandler(file_handler)

    if not config.DEBUG :
        run_daemon(main)
    else:
        main()

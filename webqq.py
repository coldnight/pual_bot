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
#   Date    :   13/11/14 13:23:49
#   Desc    :
#
from __future__ import print_function

import os
import sys
import time
import atexit
import smtplib
import logging
import traceback

from functools import partial
from email.mime.text import MIMEText


from twqq.client import WebQQClient
from twqq.requests import kick_message_handler, PollMessageRequest
from twqq.requests import system_message_handler, group_message_handler
from twqq.requests import buddy_message_handler, BeforeLoginRequest
from twqq.requests import register_request_handler, BuddyMsgRequest
from twqq.requests import Login2Request, FriendInfoRequest
from twqq.requests import sess_message_handler, discu_message_handler

import config

from server import http_server_run
from plugins import PluginLoader


logger = logging.getLogger("client")

SMTP_HOST = getattr(config, "SMTP_HOST", None)


def send_notice_email():
    """ 发送提醒邮件
    """
    if not SMTP_HOST:
        return False

    postfix = ".".join(SMTP_HOST.split(".")[1:])
    me = "bot<{0}@{1}>".format(config.SMTP_ACCOUNT, postfix)

    msg = MIMEText(""" 你的WebQQ机器人需要一个验证码,
                   请打开你的服务器输入验证码:
                   http://{0}:{1}""".format(config.HTTP_LISTEN,
                                            config.HTTP_PORT),
                   _subtype="plain", _charset="utf-8")
    msg['Subject'] = u"WebQQ机器人需要验证码"
    msg["From"] = me
    msg['To'] = config.EMAIL
    try:
        server = smtplib.SMTP()
        server.connect(SMTP_HOST)
        server.login(config.SMTP_ACCOUNT, config.SMTP_PASSWORD)
        server.sendmail(me, [config.EMAIL], msg.as_string())
        server.close()
        return True
    except Exception as e:
        traceback.print_exc()
        return False


class Client(WebQQClient):
    verify_img_path = None
    message_requests = {}
    start_time = time.time()
    msg_num = 0

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
            if getattr(config, "EMAIL_NOTICE", False):
                if send_notice_email():
                    logger.info("发送通知邮件成功")
                else:
                    logger.warning("发送通知邮件失败")
        else:
            logger.info(u"验证码本地路径为: {0}".format(self.hub.checkimg_path))
            check_code = None
            while not check_code:
                check_code = raw_input("输入验证码: ")
            self.enter_verify_code(check_code, r, uin)

    def enter_verify_code(self, code, r, uin, callback=None):
        super(Client, self).enter_verify_code(code, r, uin)
        self.verify_callback = callback
        self.verify_callback_called = False

    @register_request_handler(BeforeLoginRequest)
    def handle_verify_check(self, request, resp, data):
        if not data:
            self.handle_verify_callback(False, "没有数据返回验证失败, 尝试重新登录")
            return

        args = request.get_back_args(data)
        scode = int(args[0])
        if scode != 0:
            self.handle_verify_callback(False, args[4])

    def handle_verify_callback(self, status, msg=None):
        if not hasattr(self, "plug_loader"):
            self.plug_loader = PluginLoader(self)

        if hasattr(self, "verify_callback") and callable(self.verify_callback)\
           and not self.verify_callback_called:
            self.verify_callback(status, msg)
            self.verify_callback_called = True

    @register_request_handler(Login2Request)
    def handle_login_errorcode(self, request, resp, data):
        if not resp.body:
            return self.handle_verify_callback(False, u"没有数据返回, 尝试重新登录")

        if data.get("retcode") != 0:
            return self.handle_verify_callback(False, u"登录失败: {0}"
                                               .format(data.get("retcode")))

    @register_request_handler(FriendInfoRequest)
    def handle_frind_info_erro(self, request, resp, data):
        if not resp.body:
            self.handle_verify_callback(False, u"获取好友列表失败")
            return

        if data.get("retcode") != 0:
            self.handle_verify_callback(False, u"好友列表获取失败: {0}"
                                        .format(data.get("retcode")))
            return
        self.handle_verify_callback(True)

    @kick_message_handler
    def handle_kick(self, message):
        self.hub.relogin()

    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == "verify_required":
            if getattr(config, "AUTO_ACCEPT", True):
                self.hub.accept_verify(from_uin, account, str(account))

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        callback = partial(self.send_group_with_nick, member_nick, group_code)
        self.handle_message(send_uin, content, callback)

    @sess_message_handler
    def handle_sess_message(self, qid, from_uin, content, source):
        callback = partial(self.hub.send_sess_msg, qid, from_uin)
        self.handle_message(from_uin, content, callback, 's')

    @discu_message_handler
    def handle_discu_message(self, did, from_uin, content, source):
        nick = self.hub.get_friend_name(from_uin)
        callback = partial(self.send_discu_with_nick, nick, did)
        self.handle_message(from_uin, content, callback, 'g')

    def send_discu_with_nick(self, nick, did, content):
        content = u"{0}: {1}".format(nick, content)
        self.hub.send_discu_msg(did, content)

    def handle_message(self, from_uin, content, callback, type="g"):
        content = content.strip()
        if self.plug_loader.dispatch(from_uin, content, type, callback):
            self.msg_num += 1

    def send_group_with_nick(self, nick, group_code, content):
        content = u"{0}: {1}".format(nick, content)
        self.hub.send_group_msg(group_code, content)

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        callback = partial(self.hub.send_buddy_msg, from_uin)
        self.handle_message(from_uin, content, callback, 'b')

    @register_request_handler(PollMessageRequest)
    def handle_qq_errcode(self, request, resp, data):
        if data and data.get("retcode") in [100006]:
            logger.error(u"获取登出消息 {0!r}".format(data))
            self.hub.relogin()

        if data and data.get("retcode") in [103, 100002]:  # 103重新登陆不成功, 暂时退出
            logger.error(u"获取登出消息 {0!r}".format(data))
            exit()

    def send_msg_with_markname(self, markname, message, callback=None):
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

    def run(self, handler=None):
        self.handler = handler
        super(Client, self).run()


def run_daemon(callback, args=(), kwargs = {}):
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
    webqq = Client(config.QQ, config.QQ_PWD,
                   debug=getattr(config, "TRACE", False))
    try:
        if getattr(config, "HTTP_CHECKIMG", False):
            http_server_run(webqq)
        else:
            webqq.run()
    except KeyboardInterrupt:
        print("Exiting...", file=sys.stderr)
    except SystemExit:
        logger.error("检测到退出, 重新启动")
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    import tornado.log
    from tornado.options import options

    if not getattr(config, "DEBUG", False):
        options.log_file_prefix = getattr(config, "LOG_PATH", "log.log")
        options.log_file_max_size = getattr(
            config, "LOG_MAX_SIZE", 5 * 1024 * 1024)
        options.log_file_num_backups = getattr(config, "LOG_BACKUPCOUNT", 10)
    tornado.log.enable_pretty_logging(options=options)

    if not config.DEBUG and hasattr(os, "fork"):
        run_daemon(main)
    else:
        main()

#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/14 13:23:49
#   Desc    :
#
import config
import logging

from twqq.client import WebQQClient
from twqq.requests import system_message_handler, group_message_handler
from twqq.requests import buddy_message_handler, BeforeLoginRequest
from twqq.requests import register_request_handler, BuddyMsgRequest

from server import http_server_run


logger = logging.getLogger("client")

class Client(WebQQClient):
    verify_img_path = None
    message_requests = {}
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

            args = request.get_back_args()
            scode = int(args[0])
            if scode == 0:
                self.verify_callback(True)
            else:
                self.verify_callback(False, args[3])


    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == "verify_required":
            self.hub.accept_verify(from_uin, account, str(account))

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        self.hub.send_group_msg(group_code, u"{0}: {1}".format(member_nick, content))

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        self.hub.send_buddy_msg(from_uin, content)


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


if __name__ == "__main__":
    webqq = Client(config.QQ, config.QQ_PWD)
    if getattr(config, "HTTP_CHECKIMG", False):
        http_server_run(webqq)
    else:
        webqq.run()

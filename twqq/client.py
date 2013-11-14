#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/12 14:55:02
#   Desc    :
#
import copy
import inspect
import logging

from abc import abstractmethod
from tornado.stack_context import ExceptionStackContext
from tornadohttpclient import TornadoHTTPClient

import config

from hub import RequestHub
from requests import FirstRequest, WebQQRequest, BeforeLoginRequest
from requests import (group_message_handler, buddy_message_handler,
                      kick_message_handler, sess_message_handler,
                      system_message_handler)

logger = logging.getLogger("twqq")
class WebQQClient(object):
    """ Webqq 模拟客户端

    :param qq: QQ号
    :param pwd: 密码
    """
    def __init__(self, qq, pwd):

        self.http = TornadoHTTPClient()
        self.http.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/28.0.1500.71 Chrome/28.0.1500.71 Safari/537.36")
        self.http.debug = getattr(config, "TRACE", False)
        self.http.validate_cert = False
        self.http.set_global_headers({"Accept-Charset": "UTF-8,*;q=0.5"})

        # self.msg_disp = MessageDispatch(self)
        self.setup_msg_handlers()
        self.setup_request_handlers()
        self.hub = RequestHub(qq, pwd, self)
        self.load_request(FirstRequest())


    def load_request(self, request):
        func = self.http.get if request.method == WebQQRequest.METHOD_GET \
                else self.http.post

        kwargs = copy.deepcopy(request.kwargs)
        callback = request.callback if hasattr(request, "callback") and\
                callable(request.callback) else None
        kwargs.update(callback = self.hub.wrap(request, callback))
        kwargs.update(headers = request.headers)
        kwargs.update(delay = request.delay)

        if request.ready:
            with ExceptionStackContext(request.handle_exc):
                func(request.url, request.params, **kwargs)


    @abstractmethod
    def handle_verify_code(self, path, r, uin):
        """ 重写此函数处理验证码

        :param path: 验证码图片路径
        :param r: 接口返回
        :param uin: 接口返回
        """
        pass

    def enter_verify_code(self, code, r, uin):
        """ 填入验证码

        :param code: 验证码
        """
        self.hub.check_code = code.strip().lower()
        pwd = self.hub.handle_pwd(self.r, self.hub.check_code.upper(), self.uin)
        self.hub.load_next_request(BeforeLoginRequest(pwd))


    @group_message_handler
    def log_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        """ 处理群消息
        """
        logger.info(u"获取{0} 群的{1} 发送消息: {2}"
                    .format(group_code, member_nick, content))


    @buddy_message_handler
    def log_buddy_message(self, from_uin, content, source):
        """ 处理好友消息
        """
        logger.info(u"获取 {0} 发送的好友消息: {1}"
                     .format(from_uin, content))


    @sess_message_handler
    def log_sess_message(self, from_uin, content, source):
        """ 处理临时消息
        """
        logger.info(u"获取 {0} 发送的临时消息: {1}"
                     .format(from_uin, content))

    @kick_message_handler
    def log_kick_message(self, message):
        """ 处理被T除的消息
        """
        logger.info(u"其他地方登录了此QQ{0}".format(message))


    @system_message_handler
    def log_system_message(self, typ, from_uin, account, source):
        """ 处理系统消息
        """
        logger.info("系统消息: 类型:{0}, 发送人:{1}, 发送账号:{2}, 源:{3}"
                     .format(type, from_uin, account, source))


    def setup_msg_handlers(self):
        msg_handlers = {}
        for _, handler in inspect.getmembers(self, callable):
            if not hasattr(handler, "_twqq_msg_type"):
                continue

            if msg_handlers.has_key(handler._twqq_msg_type):
                msg_handlers[handler._twqq_msg_type].append(handler)
            else:
                msg_handlers[handler._twqq_msg_type] = [handler]

        self.msg_handlers = msg_handlers


    def setup_request_handlers(self):
        request_handlers = {}
        for _, handler in inspect.getmembers(self, callable):
            if not hasattr(handler, "_twqq_request"):
                continue

            if request_handlers.has_key(handler._twqq_request):
                request_handlers[handler._twqq_request].append(handler)
            else:
                request_handlers[handler._twqq_request] = [ handler ]

        self.request_handlers = request_handlers


    def run(self):
        self.http.start()

if __name__ == "__main__":
    webqq = WebQQClient(config.QQ, config.QQ_PWD)
    webqq.run()


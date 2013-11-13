#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/12 14:55:02
#   Desc    :
#
import copy
import logging

from tornado.stack_context import ExceptionStackContext
from tornadohttpclient import TornadoHTTPClient

import config

from requests import RequestHub, FirstRequest, WebQQRequest
from requests import (group_message_handler, buddy_message_handler,
                      kick_message_handler, sess_message_handler,
                      system_message_handler)

BASIC_KW = dict(level = logging.DEBUG if config.DEBUG else logging.INFO,
                    format = "%(asctime)s [%(levelname)s] %(message)s")
logging.basicConfig(**BASIC_KW)

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


    @group_message_handler
    def handle_group_message(self, send_nick, content, group_code,
                             send_uin, source):
        """ 处理群消息
        """
        logging.info(u"获取{0} 群的{1} 发送消息: {2}"
                    .format(group_code, send_nick, content))


    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        """ 处理好友消息
        """
        logging.info(u"获取 {0} 发送的好友消息: {1}"
                     .format(from_uin, content))


    @sess_message_handler
    def handle_sess_message(self, from_uin, content, source):
        """ 处理临时消息
        """
        logging.info(u"获取 {0} 发送的临时消息: {1}"
                     .format(from_uin, content))

    @kick_message_handler
    def handle_kick_message(self, message):
        """ 处理被T除的消息
        """
        logging.info(u"其他地方登录了此QQ{0}".format(message))


    @system_message_handler
    def handle_system_message(self, typ, from_uin, account, source):
        """ 处理系统消息
        """
        logging.info("系统消息: 类型:{0}, 发送人:{1}, 发送账号:{2}, 源:{3}"
                     .format(type, from_uin, account, source))


    def run(self):
        self.http.start()

if __name__ == "__main__":
    webqq = WebQQClient(config.QQ, config.QQ_PWD)
    webqq.run()


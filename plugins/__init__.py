#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 11:21:19
#   Desc    :   插件机制
#
import os
import inspect
import logging

logger = logging.getLogger("plugin")

class BasePlugin(object):
    """ 插件基类, 所有插件继承此基类, 并实现 hanlde_message 实例方法
    :param webqq: webqq.WebQQClient 实例
    :param http: TornadoHTTPClient 实例
    :param nickname: QQ 机器人的昵称
    :param logger: 日志
    """
    def __init__(self, webqq, http, nickname, logger = None):
        self.webqq = webqq
        self.http = http
        self.logger = logger or logging.getLogger("plugin")
        self.nickname = nickname

    def is_match(self, from_uin, content, type):
        """ 判断内容是否匹配本插件, 如匹配则调用 handle_message 方法
        :param from_uin: 发送消息人的uin
        :param content: 消息内容
        :param type: 消息类型(g: 群, s: 临时, b: 好友)
        :rtype: bool
        """
        return False

    def handle_message(self, callback):
        """ 每个插件需实现此实例方法
        :param callback: 发送消息的函数
        """
        raise NotImplemented


class PluginLoader(object):
    plugins = {}
    def __init__(self, webqq):
        self.current_path = os.path.abspath(os.path.dirname(__file__))
        self.webqq = webqq
        for m in self.list_modules():
            mobj = self.import_module(m)
            if mobj is not None:
                self.load_class(mobj)

        logger.info("Load Plugins: {0!r}".format(self.plugins))

    def list_modules(self):
        items = os.listdir(self.current_path)
        modules = [item.split(".")[0] for item in items
                   if item.endswith(".py")]
        return modules

    def import_module(self, m):
        try:
            return __import__("plugins." + m, fromlist=["plugins"])
        except:
            logger.warn("Error was encountered on loading {0}, will ignore it"
                        .format(m), exc_info = True)
            return None

    def load_class(self, m):
        for key, val in m.__dict__.items():
            if inspect.isclass(val) and issubclass(val, BasePlugin) and \
               val != BasePlugin:
                self.plugins[key] = val(self.webqq, self.webqq.hub.http,
                                        self.webqq.hub.nickname, logger)

    def dispatch(self, from_uin, content, type, callback):
        """ 调度插件处理消息
        """
        for key, val in self.plugins.items():
            if val.is_match(from_uin, content, type):
                val.handle_message(callback)
                logger.info(u"Plugin {0} handled message {1}".format(key, content))
                return True
        return False

#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/02/28 11:23:49
#   Desc    :   Web QQ API
#
import time
import json
import Queue
import random
import tempfile
import threading
from hashlib import md5
from functools import partial
from mainloop import main_loop_factory
from mainloop.interfaces import event_handler, EventHandler

from .utils import HttpHelper, get_logger, upload_file

from .message_dispatch import MessageDispatch

from .webqqevents import (CheckedEvent, WebQQLoginedEvent, BeforeLoginEvent,
                         WebQQHeartbeatEvent, WebQQMessageEvent, RetryEvent,
                         WebQQPollEvent, RemoveEvent, GroupListEvent,
                         WebQQRosterUpdatedEvent, GroupMembersEvent,
                          ReconnectEvent, FriendsUpdatedEvent)
from .handlers import (CheckHandler, BeforeLoginHandler, LoginHandler,
                       HeartbeatHandler, PollHandler, GroupMsgHandler,
                       GroupListHandler, GroupMembersHandler, WebQQHandler,
                       FriendsHandler, BuddyMsgHandler)

from utilhandlers import LongContentHandler


class WebQQ(EventHandler):
    """ WebQQ
    :param :qid QQ号
    :param :event_queue pyxmpp2时间队列"""
    def __init__(self, qid, pwd, event_queue = None):
        if event_queue:
            self.event_queue = event_queue
        else:
            self.event_queue = Queue.Queue()
        self.logger = get_logger()
        self.qid = qid                # QQ 号
        self.__pwd = pwd
        self.aid = 1003903
        self.clientid = random.randrange(11111111, 99999999)
        self.msg_id = random.randrange(1111111, 99999999)
        self.group_map = {}      # 群映射
        self.group_m_map = {}    # 群到群成员的映射
        self.uin_qid_map = {}    # uin 到 qq号的映射
        self.check_code = None
        self.skey = None
        self.ptwebqq = None
        self.require_check = False
        self.QUIT = False
        self.last_msg = {}
        self.check_data = None           # CheckHanlder返回的数据
        self.blogin_data = None          # 登录前返回的数据
        self.rc = 1
        self.start_time = time.time()
        self.hb_last_time = self.start_time
        self.poll_last_time = self.start_time
        self.connected = False
        self._helper = HttpHelper()
        self.polled = False
        self.heartbeated = False
        self.group_lst_updated = False
        self.msg_dispatch = MessageDispatch(self)
        self.mainloop = main_loop_factory(self.event_queue)
        self.mainloop.add_handler(self)
        self.http_sock = WebQQHandler.http_sock

        self.gm_updated = False       # 组成员已更新
        self.fm_updated = False       # 朋友更新成功

        self.fm_info_map = {}         # 好友信息映射

    def event(self, event, delay = 0):
        """ timeout可以延迟将事件放入事件队列 """
        if delay:
            target = partial(self.put_delay_event, self.event_queue, event, delay)
            t = threading.Thread(target = target)
            t.setDaemon(True)
            t.start()
        else:
            self.event_queue.put(event)

    def put_delay_event(self, queue, event, delay):
        """ 应当放入线程中 """
        time.sleep(delay)
        queue.put(event)

    def ptui_checkVC(self, r, vcode, uin):
        """ 处理检查的回调 返回三个值 """
        if int(r) == 0:
            self.logger.info("Check Ok")
            self.check_code = vcode
        else:
            self.logger.warn("Check Error")
            self.check_code = self.get_check_img(vcode)
            self.require_check = True
        return r, self.check_code, uin

    def get_check_img(self, vcode):
        """ 获取验证图片 """
        url = "https://ssl.captcha.qq.com/getimage"
        params = [("aid", self.aid), ("r", random.random()),
                  ("uin", self.qid)]
        helper = HttpHelper(url, params, jar = self.http_sock.cookiejar)
        res = helper.open()
        path = tempfile.mktemp()
        fp = open(path, 'wb')
        fp.write(res.read())
        fp.close()
        res = upload_file("check.jpg", path)
        print res.geturl()
        check_code = None
        while not check_code:
            check_code = raw_input("打开上面连接输出图片上的验证码: ")
        return check_code.strip().upper()

    def handle_pwd(self, password):
        """ 根据检查返回结果,调用回调生成密码和保存验证码 """
        r, self._vcode, huin = eval("self." + self.check_data.rstrip(";"))
        pwd = md5(md5(password).digest() + huin).hexdigest().upper()
        return md5(pwd + self._vcode).hexdigest().upper()

    def ptuiCB(self, scode, r, url, status, msg, nickname = None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        if int(scode) == 0:
            self.logger.info("Get ptwebqq Ok")
            self.skey = self.http_sock.cookie['.qq.com']['/']['skey'].value
            self.ptwebqq = self.http_sock.cookie['.qq.com']['/']['ptwebqq'].value
            self.logined = True
        else:
            self.logger.warn("Get ptwebqq Error")
        if nickname:
            self.nickname = nickname

    def get_qid_with_uin(self, uin):
        """ 根据uin获取QQ号 """
        url = "http://s.web2.qq.com/api/get_friend_uin2"
        params = [("tuin", uin), ("verifysession", ""),("type",4),
                  ("code", ""), ("vfwebqq", self.vfwebqq),
                  ("t", time.time())]
        self._helper.change(url, params)
        self._helper.add_header("Referer", "http://d.web2.qq.com/proxy."
                                "html?v=20110331002&callback=1&id=3")
        res = self._helper.open()
        data = res.read()
        if data:
            info = json.loads(data)
            if info.get("retcode") == 0:
                return info.get("result", {}).get("account")

    def get_group_msg_img(self, uin, info):
        """ 获取消息中的图片 """
        name = info.get("name")
        file_id = info.get("file_id")
        key = info.get("key")
        server = info.get("server")
        ip, port = server.split(":")
        gid = self.group_map.get(uin, {}).get("gid")
        url = "http://web2.qq.com/cgi-bin/get_group_pic"
        params = [("type", 0), ("gid", gid), ("uin", uin),("rip", ip),
                  ("rport", port), ("fid", file_id), ("pic", name),
                  ("vfwebqq", self.vfwebqq), ("t", time.time())]
        helper = HttpHelper(url, params)
        helper.add_header("Referer", "http://web2.qq.com/")
        return helper.open()

    def get_group_name(self, gcode):
        """ 根据gcode获取群名 """
        return self.group_map.get(gcode, {}).get("name")

    def get_group_member_nick(self, gcode, uin):
        return self.group_m_map.get(gcode, {}).get(uin, {}).get("nick")

    def run(self):
        checkhandler = CheckHandler(self)
        self.mainloop.add_handler(checkhandler)
        self.mainloop.loop()

    @event_handler(CheckedEvent)
    def handle_webqq_checked(self, event):
        """ 第一步已经完毕, 删除掉检查的handler, 将登录前handler加入mainloop"""
        bloginhandler = BeforeLoginHandler(self, password = self.__pwd)
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(bloginhandler)

    @event_handler(BeforeLoginEvent)
    def handle_webqq_blogin(self, event):
        """ 登录前完毕开始真正的登录 """
        loginhandler = LoginHandler(self)
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(loginhandler)

    @event_handler(WebQQLoginedEvent)
    def handle_webqq_logined(self, event):
        """ 登录后将获取群列表的handler放入mainloop """
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(GroupListHandler(self))
        self.mainloop.add_handler(FriendsHandler(self))

    @event_handler(FriendsUpdatedEvent)
    def handle_webqq_friends_updated(self, event):
        self.mainloop.remove_handler(event.handler)
        lst = event.data.get("result", {}).get("info", [])
        for info in lst:
            uin = info.get("uin")
            self.fm_info_map[uin] = info

    @event_handler(GroupListEvent)
    def handle_webqq_group_list(self, event):
        """ 获取群列表后"""
        self.mainloop.remove_handler(event.handler)
        data = event.data
        group_map = {}
        if data.get("retcode") == 0:
            group_list = data.get("result", {}).get("gnamelist", [])
            for group in group_list:
                gcode = group.get("code")
                group_map[gcode] = group

        self.group_map = group_map
        self.group_lst_updated = False   # 开放添加GroupListHandler
        i = 1
        for gcode in group_map:
            if i == len(group_map):
                self.mainloop.add_handler(
                    GroupMembersHandler(self, gcode = gcode, done = True))
            else:
                self.mainloop.add_handler(
                    GroupMembersHandler(self, gcode = gcode, done = False))

            i += 1

    @event_handler(GroupMembersEvent)
    def handle_group_members(self, event):
        """ 获取所有群成员 """
        self.mainloop.remove_handler(event.handler)
        members = event.data.get("result", {}).get("minfo", [])
        self.group_m_map[event.gcode] = {}
        for m in members:
            uin = m.get("uin")
            self.group_m_map[event.gcode][uin] = m
        cards = event.data.get("result", {}).get("cards", [])
        for card in cards:
            uin = card.get("muin")
            group_name = card.get("card")
            self.group_m_map[event.gcode][uin]["nick"] = group_name

        # 防止重复添加GroupListHandler
        if not self.group_lst_updated:
            self.group_lst_updated = True
            self.mainloop.add_handler(GroupListHandler(self, delay = 300))

    @event_handler(WebQQRosterUpdatedEvent)
    def handle_webqq_roster(self, event):
        """ 群成员都获取完毕后开启,Poll获取消息和心跳 """
        self.mainloop.remove_handler(event.handler)
        self.msg_dispatch.get_map()
        if not self.polled:
            self.polled = True
            self.mainloop.add_handler(PollHandler(self))
        if not self.heartbeated:
            self.heartbeated = True
            hb = HeartbeatHandler(self)
            self.mainloop.add_handler(hb)
        self.connected = True

    @event_handler(WebQQHeartbeatEvent)
    def handle_webqq_hb(self, event):
        """ 心跳完毕后, 延迟60秒在此触发此事件 重复心跳 """
        self.mainloop.remove_handler(event.handler)
        self.hb_handler = HeartbeatHandler(self, delay = 60)
        self.mainloop.add_handler(self.hb_handler)

    @event_handler(WebQQPollEvent)
    def handle_webqq_poll(self, event):
        """ 延迟1秒重复触发此事件, 轮询获取消息 """
        self.mainloop.remove_handler(event.handler)
        self.mainloop.add_handler(PollHandler(self))

    @event_handler(WebQQMessageEvent)
    def handle_webqq_msg(self, event):
        """ 有消息到达, 处理消息 """
        self.msg_dispatch.dispatch(event.message)

    @event_handler(RetryEvent)
    def handle_retry(self, event):
        """ 有handler触发异常, 需重试 """
        times = event.get_retry_times()
        if times <= 10:
            self.mainloop.remove_handler(event.handler)
            handler = event.cls(self, event.req, *event.args, **event.kwargs)
            self.mainloop.add_handler(handler)
        else:
            self.logger.info(u"{0} retry too much, will retry leater"\
                             .format(event.handler))
            self.event(event, times * 2)

    @event_handler(RemoveEvent)
    def handle_remove(self, event):
        """ 触发此事件, 移除handler """
        self.mainloop.remove_handler(event.handler)

    @event_handler(ReconnectEvent)
    def handle_reconnect(self, event):
        self.mainloop.remove_handler(event.handler)
        self.mainloop.remove_handler(self.hb_handler)
        self.run()

    @event_handler()
    def handle_all(self, event):
        self.logger.info(u"-- {0}".format(event))

    def send_group_msg(self, group_uin, content):
        """ 发送qq群消息 """
        if len(content) > 150:
            callback = partial(self.send_group_msg, group_uin)
            handler = LongContentHandler(self, content = content, callback = callback)
        else:
            handler = GroupMsgHandler(self, group_uin = group_uin,
                                  content = content)
        self.mainloop.add_handler(handler)

    def send_buddy_msg(self, to_uin, content):
        """ 发送好友消息 """
        if len(content) > 150:
            callback = partial(self.send_group_msg, to_uin)
            handler = LongContentHandler(self, content = content, callback = callback)
        else:
            handler = BuddyMsgHandler(self, to_uin = to_uin, content = content)
        self.mainloop.add_handler(handler)

    def make_msg_content(self, content):
        """ 构造QQ消息的内容 """
        return json.dumps([content, ["font", {"name":"Monospace", "size":10,
                                   "style":[0, 0, 0], "color":"000000"}]])

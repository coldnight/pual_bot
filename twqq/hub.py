#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/14 13:14:54
#   Desc    :   请求中间件
#
import re
import os
import time
import json
import random
import urllib2
import logging
import tempfile
import threading

import _hash

from hashlib import md5

from tornadohttpclient import UploadForm as Form

from .requests import check_request, AcceptVerifyRequest
from .requests import WebQQRequest, PollMessageRequest, HeartbeatRequest
from .requests import SessMsgRequest, BuddyMsgRequest, GroupMsgRequest

logger = logging.getLogger("twqq")

class RequestHub(object):
    SIG_RE = re.compile(r'var g_login_sig=encodeURIComponent\("(.*?)"\);')
    def __init__(self, qid, pwd, client = None):
        self.qid = qid
        self.__pwd = pwd
        self.client = client
        self.rc = random.randrange(0, 100)
        self.aid = 1003903                                    # aid 固定
        self.clientid = random.randrange(11111111, 99999999)  # 客户端id 随机固定
        self.msg_id = random.randrange(11111111, 99999999)     # 消息id, 随机初始化
        self.daid = 164
        self.login_sig = None
        self.ptwebqq = None
        self.nickname = None
        self.vfwebqq = None
        self.psessionid = None

        # 检查是否验证码的回调
        self.ptui_checkVC = lambda r, v, u: (r, v, u)

        # 是否需要验证码
        self.require_check = None
        self.require_check_time = None

        # 是否开始心跳和拉取消息
        self.poll_and_heart = None
        self.login_time = None
        self.hThread = None

        # 验证图片
        self.checkimg_path = tempfile.mktemp(".jpg")
        self._lock_path = tempfile.mktemp()
        self._wait_path = tempfile.mktemp()

        self.friend_info = {}        # 初始化好友列表
        self.group_info = {}         # 初始化组列表
        self.group_sig = {}          # 组签名映射, 用作发送临时消息(sess_message)
        self.group_members_info = {} # 初始化组成员列表
        self.mark_to_uin = {}        # 备注名->uin的映射

        self.message_interval = 0.5  # 消息间隔
        self.last_msg_time = time.time()
        self.last_msg_content = None
        self.last_msg_numbers = 0    # 剩余位发送的消息数量
        WebQQRequest.hub = self


    def load_next_request(self, request):
        self.client.load_request(request)


    def setup_handler(self, r, vcode, uin, next_request):
        self.handler.r = r
        self.handler.vcode = vcode
        self.handler.uin = uin
        #TODO
        self.handler.next_request = next_request

    def handle_pwd(self, r, vcode, huin):
        """ 根据检查返回结果,调用回调生成密码和保存验证码 """
        pwd = md5(md5(self.__pwd).digest() + huin).hexdigest().upper()
        pwd = md5(pwd + vcode).hexdigest().upper()
        return pwd


    def upload_file(self, filename, path):
        """ 上传文件

        :param filename: 文件名
        :param path: 文件路径
        """
        form = Form()
        filename = filename.encode("utf-8")
        form.add_file(fieldname='name', filename=filename,
                        fileHandle=open(path))
        img_host = "http://dimg.vim-cn.com/"
        req = urllib2.Request(img_host)
        req.add_header("Content-Type", form.get_content_type())
        req.add_header("Content-Length", len(str(form)))
        req.add_header("User-Agent", "curl/python")
        req.add_data(str(form))
        return urllib2.urlopen(req)


    def lock(self):
        with open(self._lock_path, 'w'):
            pass


    def unlock(self):
        if os.path.exists(self._lock_path):
            os.remove(self._lock_path)


    def clean(self):
        self.unlock()
        if os.path.exists(self._wait_path):
            os.remove(self._wait_path)


    def wait(self):
        with open(self._wait_path, 'w'):
            pass


    def run_daemon(self, func, *args, **kwargs):
        pass


    def _hash(self):
        """  获取列表时的Hash """
        return _hash.webqq_hash(self.qid, self.ptwebqq)


    def start_poll(self):
        if not self.poll_and_heart:
            self.login_time = time.time()
            logger.info("开始拉取信息和心跳")
            self.load_next_request(PollMessageRequest())
            self.poll_and_heart = True
            self.hThread = threading.Thread(target = self._heartbeat)
            self.hThread.setDaemon(True)
            self.hThread.start()


    def _heartbeat(self):
        assert not isinstance(threading.currentThread(), threading._MainThread)
        while 1:
            self.load_next_request(HeartbeatRequest())
            time.sleep(60)



    def make_msg_content(self, content):
        """ 构造QQ消息的内容 """
        self.msg_id += 1
        return json.dumps([content, ["font", {"name":"Monospace", "size":10,
                                   "style":[0, 0, 0], "color":"000000"}]])


    def get_delay(self, content):
        MIN = self.message_interval
        delay = 0
        sub = time.time() - self.last_msg_time
        if self.last_msg_numbers < 0:
            self.last_msg_numbers = 0

        # 不足最小间隔就补足最小间隔
        if sub < MIN:
            delay = MIN
            logger.debug(u"间隔 %s 小于 %s, 设置延迟为%s", sub, MIN, delay)

        # 如果间隔是已有消息间隔的2倍, 则清除已有消息数
        #print "sub", sub, "n:", self.last_msg_numbers
        if self.last_msg_numbers > 0 and sub / (MIN * self.last_msg_numbers)> 1:
            self.last_msg_numbers = 0

        # 如果还有消息未发送, 则加上他们的间隔
        if self.last_msg_numbers > 0:
            delay += MIN * self.last_msg_numbers
            logger.info(u"有%s条消息未发送, 延迟为 %s", self.last_msg_numbers, delay)


        n = 1
        # 如果这条消息和上条消息一致, 保险起见再加上一个最小间隔
        if self.last_msg_content == content and sub < MIN:
            delay += MIN
            self.last_msg_numbers += 1
            n = 2

        self.last_msg_numbers += 1
        self.last_msg_content = content

        if delay:
            logger.info(u"有 {1} 个消息未投递将会在 {0} 秒后投递"
                         .format(delay, self.last_msg_numbers))
        # 返回消息累加个数, 在消息发送后减去相应的数目
        return delay, n

    def consume_delay(self, number):
        """ 消费延迟
        """
        self.last_msg_numbers -= number
        self.last_msg_time = time.time()


    def get_group_id(self, uin):
        """ 根据组uin获取组的id
        """
        return self.group_info.get(uin, {}).get("gid")


    def wrap(self, request, func = None):
        """ 装饰callback
        """
        def _wrap(resp, *args, **kwargs):
            data = resp.body
            logger.debug(resp.headers)
            if resp.headers.get("Content-Type") == "application/json":
                data = json.loads(data) if data else {}
            else:
                try:
                    data = json.loads(data)
                except:
                    pass
            if func:
                func(resp, data, *args, **kwargs)

            funcs = self.client.request_handlers.get(check_request(request), [])
            for f in funcs:
                f(resp, data)

        return _wrap


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


    def get_group_member_nick(self, gcode, uin):
        return self.group_members_info.get(gcode, {}).get(uin, {}).get("nick")


    def dispatch(self, qq_source):
        if qq_source.get("retcode") == 0:
            messages = qq_source.get("result")
            for m in messages:
                funcs = self.client.msg_handlers.get(m.get("poll_type"))
                [func(*func._args_func(self, m)) for func in funcs]


    def send_sess_msg(self, to_uin, content):
        """ 发送临时消息

        :param to_uin: 消息接收人
        :param content: 消息内容
        """
        self.load_next_request(SessMsgRequest(to_uin, content))


    def send_group_msg(self, group_uin, content):
        """ 发送群消息

        :param group_uin: 组的uin
        :param content: 消息内容
        """
        self.load_next_request(GroupMsgRequest(group_uin, content))


    def send_buddy_msg(self, to_uin, content):
        """ 发送好友消息

        :param to_uin: 消息接收人
        :param content: 消息内容
        """
        self.load_next_request(BuddyMsgRequest(to_uin, content))

    def accept_verify(self, uin, account, markname = ""):
        """ 同意验证请求

        :param  uin: 请求人uin
        :param account: 请求人账号
        :param markname: 添加后的备注
        """
        self.load_next_request(AcceptVerifyRequest(uin, account, markname))

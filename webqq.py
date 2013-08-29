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
#   Date    :   13/04/19 09:49:56
#   Desc    :   WebQQ
#

import re
import os
import sys
import time
import json
import atexit
import random
import logging
import traceback

from hashlib import md5
from functools import partial
from datetime import datetime

from tornadohttpclient import TornadoHTTPClient
from message_dispatch import MessageDispatch
from command import upload_file
from config import UPLOAD_CHECKIMG, Set_Password
try:
    from config import MESSAGE_INTERVAL
except ImportError:
    MESSAGE_INTERVAL = 0.5

try:
    from config import DEBUG
except ImportError:
    DEBUG = True

try:
    from config import TRACE
except:
    TRACE = False

BASIC_KW = dict(level = logging.DEBUG if DEBUG else logging.INFO,
                    format = "%(asctime)s [%(levelname)s] %(message)s")
logging.basicConfig(**BASIC_KW)

SIG_RE = re.compile(r'var g_login_sig=encodeURIComponent\("(.*?)"\);')


class WebQQ(object):
    def __init__(self, qid, pwd):
        self.qid = qid               # QQ 号
        self.__pwd = pwd             # QQ密码
        self.nickname = None         # 初始化QQ昵称
        self.http = TornadoHTTPClient()
        self.http.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/28.0.1500.71 Chrome/28.0.1500.71 Safari/537.36")
        self.http.debug = TRACE
        self.http.validate_cert = False
        self.http.set_global_headers({"Accept-Charset": "UTF-8,*;q=0.5"})
        self.msg_dispatch = MessageDispatch(self)

        self.rc = random.randrange(0, 100)

        self.aid = 1003903                                    # aid 固定
        self.clientid = random.randrange(11111111, 99999999)  # 客户端id 随机固定
        self.msg_id = random.randrange(1111111, 99999999)     # 消息id, 随机初始化

        self.require_check = False   # 是否需要验证码
        self.poll_and_heart = False  # 开始拉取消息和心跳

        # 初始化WebQQ登录期间需要保存的数据
        self.check_code = None
        self.ptwebqq = None

        self.check_data = None       # 初始化检查时返回的数据
        self.blogin_data = None      # 初始化登录前返回的数据

        self.friend_info = {}        # 初始化好友列表
        self.group_info = {}         # 初始化组列表
        self.group_sig = {}          # 组签名映射, 用作发送临时消息(sess_message)
        self.group_members_info = {} # 初始化组成员列表

        self.hb_time = int(time.time() * 1000)
        self.daid = 164
        self.login_sig = None

        self.login_time = None       # 登录的时间
        self.last_msg_time = time.time()
        self.last_msg_content = None
        self.last_msg_numbers = 0    # 剩余位发送的消息数量
        self.base_header = {"Referer":"https://d.web2.qq.com/cfproxy.html?v=20110331002&callback=1"}

        self.last_heartbeat = None


    def ptuiCB(self, scode, r, url, status, msg, nickname = None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        if int(scode) == 0:
            logging.info("从Cookie中获取ptwebqq的值")
            self.ptwebqq = self.http.cookie['.qq.com']['/']['ptwebqq'].value
            self.logined = True
        elif int(scode) == 4:
            logging.error(msg)
            self.check()
        else:
            logging.error(u"server response: {0}".format(msg.decode('utf-8')))
            exit(2)

        if nickname:
            self.nickname = nickname


    def get_group_member_nick(self, gcode, uin):
        return self.group_members_info.get(gcode, {}).get(uin, {}).get("nick")

    def get_uptime(self):
        MIN = 60
        HOUR = 60 * MIN
        DAY = 24 * HOUR
        up_time = datetime.fromtimestamp(self.login_time).strftime("%H:%M:%S")

        now = time.time()
        sub = now - self.login_time

        days = int(sub / DAY)
        hours = int(sub / HOUR)
        mins = int(sub / MIN)

        if mins:
            num = mins
            unit = "min"

        if hours:
            num = hours
            unit = "hours" if hours > 1 else "hour"

        if days:
            num = days
            unit = "days" if days > 1 else "day"

        if not days and not mins and not hours:
            num = int(sub)
            unit = "sec"

        return "{0} up {1} {2}".format(up_time, num, unit)


    def get_login_sig(self):
        logging.info("获取 login_sig...")
        url = "https://ui.ptlogin2.qq.com/cgi-bin/login"
        params = [("daid", self.daid), ("target", "self"), ("style", 5),
                  ("mibao_css", "m_webqq"), ("appid", self.aid),
                  ("enable_qlogin", 0), ("no_verifyimg", 1),
                  ("s_url", "http://web2.qq.com/loginproxy.html"),
                  ("f_url", "loginerroralert"),
                  ("strong_login", 1), ("login_state", 10),
                  ("t", "20130723001")]
        self.http.get(url, params, callback = self._get_login_sig)
        self.http.get("http://web2.qq.com")

    def _get_login_sig(self, resp):
        sigs = SIG_RE.findall(resp.body)
        if len(sigs) == 1:
            self.login_sig = sigs[0]
            logging.info(u"获取Login Sig: {0}".format(self.login_sig))
        else:
            logging.warn(u"没有获取到 Login Sig, 后续操作可能失败")
            self.login_sig = ""

        self.check()



    def check(self):
        """ 检查是否需要验证码
        url :
            https://ssl.ptlogin2.qq.com/check
        方法:   GET
        参数:
            {
                uin     // qq号
                appid   // 程序id 固定为1003903
                r       // 随机数
                u1      // http://web2.qq.com/loginproxy.html
                js_ver  // 10040
                js_type // 0
            }
        返回:
            ptui_checkVC('0','!PTH','\x00\x00\x00\x00\x64\x74\x8b\x05');
            第一个参数表示状态码, 0 不需要验证, 第二个为验证码, 第三个为uin
        """

        logging.info(u"检查是否需要验证码...")
        #url = "https://ssl.ptlogin2.qq.com/check"
        url = "http://check.ptlogin2.qq.com/check"
        params = {"uin":self.qid, "appid":self.aid,
                  "u1": "http://web2.qq.com/loginproxy.html",
                  "login_sig":self.login_sig, "js_ver":10040,
                  "js_type":0, "r" : random.random()}
        headers = {"Referer":"https://ui.ptlogin2.qq.com/cgi-bin/login?daid="
                   "164&target=self&style=5&mibao_css=m_webqq&appid=1003903&"
                   "enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb2.q"
                   "q.com%2Floginproxy.html&f_url=loginerroralert&strong_log"
                   "in=1&login_state=10&t=20130723001"}
        self.http.get(url, params, headers = headers, callback = self.handle_verify)

        cookie_url = "http://www.simsimi.com/talk.htm?lc=ch"
        cookie_params = (("lc", "ch"),)
        headers = {"Referer": "http://www.simsimi.com/talk.htm"}
        self.http.get(cookie_url, cookie_params, headers = headers)

        headers = {"Referer": "http://www.simsimi.com/talk.htm?lc=ch"}
        self.http.get("http://www.simsimi.com/func/langInfo",
                             cookie_params, headers = headers)


    def handle_pwd(self, r, vcode, huin):
        """ 根据检查返回结果,调用回调生成密码和保存验证码 """
        pwd = md5(md5(self.__pwd).digest() + huin).hexdigest().upper()
        pwd = md5(pwd + vcode).hexdigest().upper()
        return pwd


    def get_check_img(self, r, vcode, uin):
        """ 获取验证图片 """

        def callback(resp):
            path = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                                "check.jpg")
            fp = open(path, 'wb')
            fp.write(resp.body)
            fp.close()
            if UPLOAD_CHECKIMG:
                res = upload_file("check.jpg", path)
                path = res.read()
            print u"验证图片: {0}".format(path)
            check_code = ""
            while not check_code:
                check_code = raw_input("输入验证图片上的验证码: ")
            ccode = check_code.strip().lower()
            self.check_code = ccode
            pwd = self.handle_pwd(r, ccode.upper(), uin)
            self.before_login(pwd)

        url = "https://ssl.captcha.qq.com/getimage"
        params = [("aid", self.aid), ("r", random.random()),
                ("uin", self.qid)]
        self.http.get(url, params, callback = callback)


    def handle_verify(self, resp):
        ptui_checkVC = lambda r, v, u: (r, v, u)
        r, vcode, uin = eval(resp.body.strip().rstrip(";"))
        if int(r) == 0:
            logging.info("验证码检查完毕, 不需要验证码")
            password = self.handle_pwd(r, vcode, uin)
            self.before_login(password)
            self.check_code = vcode
        else:
            logging.warn("验证码检查完毕, 需要验证码")
            self.get_check_img(r, vcode, uin)
            self.require_check = True


    def before_login(self, password):
        """ 登录之前的操作
        url:
            https://ssl.ptlogin2.qq.com/login
        方法:   GET
        参数:
            {
                u       // qq号码
                p       // 经过处理的密码
                verifycode  // 验证码
                webqq_type  // 固定为10
                remember_uin    // 是否记住qq号, 传1 即可
                login2qq        // 登录qq, 传1
                aid             // appid 固定为 1003903
                u1              // 固定为 http://www.qq.com
                h               // 固定为1
                ptrediect       // 固定为0
                ptlang          // 固定为2052
                from_ui         // 固定为 1
                pttype          // 固定为1
                dumy            // 固定为空
                fp              // 固定为loginerroralert ( 重要)
                mibao_css       // 固定为 m_webqq
                t               // 固定为1
                g               // 固定为
                js_type         // 固定为0
                js_ver          // 固定为10021
        其他:
            如果check步骤验证了需要验证码, 需加上 Referer头 值为:
            https://ui.ptlogin2.qq.com/cgi-bin/login?target=self&style=5&mibao_css=m_webqq&appid=1003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Floginproxy.html&f_url=loginerroralert&strong_login=1&login_state=10&t=20130221001

        接口返回:
            ptuiCB('0','0','http://www.qq.com','0','登录成功!', 'nickname');
        先检查是否需要验证码,不需要验证码则首先执行一次登录
        然后获取Cookie里的ptwebqq保存在实例里,供后面的接口调用
        """
        url = "https://ssl.ptlogin2.qq.com/login"
        params = [("u",self.qid), ("p",password), ("verifycode", self.check_code),
                  ("webqq_type",10), ("remember_uin", 1),("login2qq",1),
                  ("aid", self.aid), ("u1", "http://www.qq.com/loginproxy.h"
                                      "tml?login2qq=1&webqq_type=10"),
                  ("h", 1), ("action", 4-5-8246),
                  ("ptredirect", 0), ("ptlang", 2052), ("from_ui", 1),
                  ("daid", self.daid),
                  ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                  ("mibao_css","m_webqq"), ("t",1), ("g",1), ("js_type",0),
                  ("js_ver", 10040), ("login_sig", self.login_sig)]
        headers = {}
        if self.require_check:
            headers.update(Referer =  "https://ui.ptlogin2.qq.com/cgi-"
                            "bin/login?target=self&style=5&mibao_css=m_"
                            "webqq&appid=1003903&enable_qlogin=0&no_ver"
                            "ifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Fl"
                            "oginproxy.html&f_url=loginerroralert&stron"
                            "g_login=1&login_state=10&t=20130221001")
        logging.info("检查完毕, 开始登录前准备")
        self.http.get(url, params, headers = headers, callback = self.login0)


    def login0(self, resp):
        logging.info("开始登录前准备...")
        blogin_data = resp.body.decode("utf-8").strip().rstrip(";")
        eval("self." + blogin_data)

        location1 = re.findall(r'ptuiCB\(\'0\'\,\'0\'\,\'(.*)\'\,\'0\'\,',
                               blogin_data)[0]
        params = []
        header = {"Referer": "https://ui.ptlogin2.qq.com/cgi-bin/login?d"
                  "aid=164&target=self&style=5&mibao_css=m_webqq&appid=1"
                  "003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2"
                  "F%2Fweb2.qq.com%2Floginproxy.html&f_url=loginerrorale"
                  "rt&strong_login=1&login_state=10&t=20130723001"}
        self.http.get(location1, params, headers = header,
                      callback = self.get_location1)

    def get_location1(self, resp):
        logging.info("准备完毕, 开始登录")
        self.login()


    def login(self):
        """ 获取登录前的数据, 并进行登录
        url:
            http://d.web2.qq.com/channel/login2
        方法: POST
        参数:
            {
                r : {
                    status      // 登录后的状态 ("online")
                    ptwebqq     // 上次请求返回的cookie
                    passwd_sig  // 固定为空
                    clientid    // 随机的clientid
                    psessionid  // 传递 null
                }
                clientid    // 客户端id
                psessionid  // 传递null
            }
        其他:
            需加上 Referer和 Origin 头:
            "Referer": "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3"
            "Origin": "http://d.web2.qq.com"

        返回:
            {u'retcode': 0,
            u'result': {
                'status': 'online', 'index': 1075,
                'psessionid': '', u'user_state': 0, u'f': 0,
                u'uin': 1685359365, u'cip': 3673277226,
                u'vfwebqq': u'', u'port': 43332}}
            保存result中的psessionid和vfwebqq供后面接口调用
        """
        time.sleep(4)

        url = "http://d.web2.qq.com/channel/login2"
        params = [("r", '{"status":"online","ptwebqq":"%s","passwd_sig":"",'
                '"clientid":"%d","psessionid":null}'\
                % (self.ptwebqq, self.clientid)),
                ("clientid", self.clientid),
                ("psessionid", "null")
                ]

        headers = { "Origin": "http://d.web2.qq.com"}
        headers.update(self.base_header)
        logging.info("登录准备完毕, 开始登录")
        self.http.post(url, params, headers = headers,
                              callback= self.update_friend)

    def _hash(self):
        a = str(self.qid)
        e = self.ptwebqq
        l = len(e)
        # 将qq号码转换成整形列表
        b, k, d = 0, -1, 0
        for d in a:
            d = int(d)
            b += d
            b %= l
            f = 0
            if b + 4 > l:
                g = 4 + b - l
                for h in range(4):
                    f |= h < g and (
                        ord(e[b + h]) & 255) << (3 - h) * 8 or (
                            ord(e[h - g]) & 255) << (3 - h) * 8
            else:
                for h in range(4):
                    f |= (ord(e[b + h]) & 255) << (3 - h) * 8
            k ^= f
        c = [k >> 24 & 255, k >> 16 & 255, k >> 8 & 255, k & 255]
        import string
        k = list(string.digits) + ['A', 'B', 'C', 'D', 'E', 'F']
        d = [k[b >> 4 & 15] + k[b & 15] for b in c]
        return ''.join(d)


    def update_friend(self, resp, login = True):
        """ 更新好友列表
        URL:
            http://s.web2.qq.com/api/get_user_friends2
        METHOD:
            POST
        PARAMS:
            {r:{"h":"hello", "vfwebqq":""}}
        HEADER:
            Referer:http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1
        """

        data = json.loads(resp.body)
        if login:
            if data.get("retcode") != 0:
                logging.error("获取好友列表失败 {0!r}".format(data))
                return
            self.vfwebqq = data.get("result", {}).get("vfwebqq")
            self.psessionid = data.get("result", {}).get("psessionid")


        url = "http://s.web2.qq.com/api/get_user_friends2"
        params = [("r", json.dumps({"h":"hello", "hash":self._hash(),
                                    "vfwebqq":self.vfwebqq}))]
        headers = {"Referer":
            "http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1"}

        callback = self.update_friend

        if login:
            logging.info("登录成功")
            if not DEBUG:
                aw = ""
                while aw.lower() not in ["y", "yes", "n", "no"]:
                    aw = raw_input("是否将程序至于后台[y] ")
                    if not aw:
                        aw = "y"

                if aw in ["y", "yes"]:
                    run_daemon(self.http.post, args = (url, params),
                               kwargs = dict(headers = headers,
                                             kwargs = dict(login = False),
                                             callback = callback))
                    return

            self.http.post(url, params, headers = headers,
                           callback = callback, kwargs = dict(login = False))
        else:
            lst = data.get("result", {}).get("info", [])
            for info in lst:
                uin = info.get("uin")
                self.friend_info[uin] = info
            logging.debug("加载好友信息 {0!r}".format(self.friend_info))
            self.update_group()

            self.http.post(url, params, headers = self.base_header,
                                  delay = 300, callback = callback)


    def update_group(self, resp = None):
        """ 获取组列表, 并获取组成员
        获取组列表:
            url:
                http://s.web2.qq.com/api/get_group_name_list_mask2
            method:
                POST
            params:
                {
                    r : {
                        vfwebqq     // 登录前返回的cookie值
                    }
                }

        """
        logging.info("获取群列表")
        url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
        params = [("r", '{"vfwebqq":"%s"}' % self.vfwebqq),]
        headers = {"Origin": "http://s.web2.qq.com"}
        headers.update(self.base_header)
        self.http.post(url, params, headers = headers,
                              callback = self.group_members)


    def group_members(self, resp):
        """ 获取群列表, 获取群列表中的成员
        url: http://s.web2.qq.com/api/get_group_info_ext2
        method: GET
        params:
            {
                gcode           // 群代码
                vfwebqq         // 登录前的cookie值
                t               // int(time.time())
            }
        headers:
            "Referer":
            "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3"
        """
        logging.info("加载组成员信息")
        data = json.loads(resp.body)
        logging.debug(u"群信息 {0!r}".format(data))
        group_list = data.get("result", {}).get("gnamelist", [])
        logging.debug(u"群列表: {0!r}".format(group_list))
        if not group_list:
            self.heartbeat(0)
            self.poll()

        for i, group in enumerate(group_list):
            gcode = group.get("code")
            url = "http://s.web2.qq.com/api/get_group_info_ext2"
            params = [("gcode", gcode),("vfwebqq", self.vfwebqq),
                      ("cb", "undefine"), ("t", int(time.time()))]

            if i == len(group_list) -1 :
                kwargs = dict(gcode = gcode, last = True)
            else:
                kwargs = dict(gcode = gcode)

            self.http.get(url, params, headers = self.base_header,
                          callback = self.do_group_members, kwargs = kwargs)

            self.group_info[gcode] = group


    def do_group_members(self, resp, gcode, last = False):
        """ 获取群成员数据 """
        data = json.loads(resp.body)
        logging.debug(u"获取群成员信息 {0!r}".format(data))
        members = data.get("result", {}).get("minfo", [])
        self.group_members_info[gcode] = {}
        for m in members:
            uin = m.get("uin")
            self.group_members_info[gcode][uin] = m

        cards = data.get("result", {}).get("cards", [])

        for card in cards:
            uin = card.get("muin")
            group_name = card.get("card")
            self.group_members_info[gcode][uin]["nick"] = group_name

        logging.debug(u"群成员信息: {0!r}".format(self.group_members_info))


        if last and not self.poll_and_heart:
            logging.info("万事具备,开始拉取信息和心跳")
            self.login_time = time.time()
            self.poll()
            self.heartbeat(0)


    def poll(self):
        """ 建立长连接获取消息
        url:http://d.web2.qq.com/channel/poll2
        方法: POST
        参数:
            {
                r:{
                    clientid       // 客户端id
                    psessionid     // session id
                    key             // 固定为0
                    ids             // 固定为 []
                }
                clientid
                psessionid
            }

        头部:
            "Referer": "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=2"
        """
        if not self.poll_and_heart:
            self.poll_and_heart = True
        url = "http://d.web2.qq.com/channel/poll2"
        rdic = {"clientid": self.clientid, "psessionid": self.psessionid,
                "key": 0, "ids":[]}
        params = [("r", json.dumps(rdic)), ("clientid", self.clientid),
                ("psessionid", self.psessionid)]
        headers = {"Referer":"https://d.web2.qq.com/cfproxy.html?v=20110331002&callback=1",
                   "Origin":"http://d.web2.qq.com"}

        self.http.post(url, params, headers = headers, request_timeout = 60.0,
                       connect_timeout = 60.0, callback = self.handle_msg)


    def handle_msg(self, resp):
        """ 处理消息 """
        self.poll()
        self.check_heartbeat()
        if not resp.body:
            return

        data = resp.body
        try:
            msg = json.loads(data)
            if msg.get("retcode") in [121, 103]:
                logging.error(u"获取消息异常 {0!r}".format(data))
                return
            logging.info(u"获取消息: {0!r}".format(msg))
            self.msg_dispatch.dispatch(msg)
        except ValueError:
            if DEBUG:
                traceback.print_exc()
            logging.error(u"消息加载失败: %s", data)


    def check_heartbeat(self):
        if self.last_heartbeat and (time.time() - self.last_heartbeat) > 240:
            logging.warn(u"心跳中断, 重启心跳..")
            self.heartbeat(0)


    def heartbeat(self, delay = 60):
        """ 开始心跳
        url:http://web.qq.com/web2/get_msg_tip
        方法: GET
        参数:
            {
                uin  // 固定为空
                tp   // 固定为1
                rc   // 固定为1
                id   // 固定位0
                lv   // 固定为2
                t    // 开始的心跳时间(int(time.time()) * 1000)
            }
        """

        if not self.poll_and_heart:
            self.poll_and_heart = True

        url = "http://web.qq.com/web2/get_msg_tip"
        params = [("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                    ("rc", self.rc), ("lv", 3),
                ("t", int(self.hb_time * 1000))]
        self.rc += 1

        self.http.get(url, params, callback = self.hb_next, delay = delay)


    def hb_next(self, resp):
        """ 持续心跳 """
        logging.info("心跳..")
        self.last_heartbeat = time.time()
        self.heartbeat()


    def make_msg_content(self, content):
        """ 构造QQ消息的内容 """
        self.msg_id += 1
        return json.dumps([content, ["font", {"name":"Monospace", "size":10,
                                   "style":[0, 0, 0], "color":"000000"}]])


    def get_sess_group_sig(self, to_uin, callback):
        """ 获取临时消息组签名
        URL: http://d.web2.qq.com/channel/get_c2cmsg_sig2
        METHOD: GET
        PARAMS:
            id   // 请求ID 固定为833193360
            to_uin   // 消息接受人uin( 消息的from_uin)
            service_type   // 固定为0
            clientid       // 客户端id
            psessionid     // session id
            t              // 当前时间秒1370671760656
        HEADERS:
        Referer:http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3
        """
        url = "http://d.web2.qq.com/channel/get_c2cmsg_sig2"
        params = (("id", 833193360), ("to_uin", to_uin), ("service_type", 0),
                  ("clientid", self.clientid), ("psessionid", self.psessionid),
                  ("t", time.time()))


        def callback(resp):
            data = resp.body
            r = json.loads(data)
            result = r.get("result")
            group_sig = result.get("value")
            if r.get("retcode") != 0:
                logging.warn(u"加载临时消息签名失败: {0}".format(group_sig))
                return
            try:
                logging.info("加载临时消息签名 {0} for {1}".format(group_sig, to_uin))
            except UnicodeError:
                return
            self.group_sig[to_uin] = group_sig
            callback()

        self.http.get(url, params, callback = callback, headers = self.base_header)


    def send_sess_msg(self, to_uin, content):
        """ 发送临时消息
        URL:http://d.web2.qq.com/channel/send_sess_msg2
        METHOD: POST
        PARAMS:
            r:{
                to              // 消息接收人 uin
                group_sig       // 组签名
                face            // 固定为 564,
                content         // 发送内容
                msg_id          // 消息id
                service_type    // 固定为0,
                clientid        // 客户端id
                psessionid      // sessionid
                }
            clientid                // 客户端id
            psessionid              // sessionid
        Headers:
            self.base_header
        """
        group_sig = self.group_sig.get(to_uin)
        if not group_sig:
            callback = partial(self.send_sess_msg, to_uin, content)
            return self.get_sess_group_sig(to_uin, callback)

        logging.info(u"发送临时消息 {0} 到 {1}".format(content, to_uin))
        delay, n = self.get_delay(content)
        content = self.make_msg_content(content)
        url = "http://d.web2.qq.com/channel/send_sess_msg2"
        params = (("r", json.dumps({"to":to_uin, "group_sig":group_sig,
                                    "face":564, "content":content,
                                    "msg_id": self.msg_id, "service_type":0,
                                    "clientid":self.clientid,
                                    "psessionid":self.psessionid})),
                  ("clientid", self.clientid), ("psessionid", self.psessionid))
        def callback(resp):
            self.last_msg_numbers -= n
            self.last_msg_time = time.time()

        self.http.post(url, params, headers = self.base_header,
                              callback = callback, delay = delay)


    def send_buddy_msg(self, to_uin, content):
        """ 发送好友消息
        URL:
            http://d.web2.qq.com/channel/send_buddy_msg2

        METHOD:
            POST

        PARAMS:
            {
                "r":{
                    "to"            // 好友uin
                    "face"          // 固定为564
                    "content"       // 发送内容
                    "msg_id"        // 消息id, 每发一条递增
                    "clientid"      // 客户端id
                    "psessionid"    // sessionid
                    }
                "clientid":clientid,
                "psessionid": psessionid,
            }

        HEADERS:
            Referer:http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3
        """
        logging.info(u"发送好友消息 {0} 给 {1}".format(content, to_uin))
        content = self.make_msg_content(content)

        url = "http://d.web2.qq.com/channel/send_buddy_msg2"

        r = {"to":to_uin, "face":564, "content":content,
             "clientid":self.clientid, "msg_id": self.msg_id,
             "psessionid": self.psessionid}
        params = [("r",json.dumps(r)), ("clientid",self.clientid),
                  ("psessionid", self.psessionid)]
        headers = {"Origin": "http://d.web2.qq.com"}
        headers.update(self.base_header)
        delay, n = self.get_delay(content)
        def callback(resp):
            self.last_msg_numbers -= n
            self.last_msg_time = time.time()

        self.http.post(url, params, headers = headers, delay = delay,
                              callback = callback)


    def send_group_msg(self, group_uin, content):
        """ 发送群消息
        url:http://d.web2.qq.com/channel/send_qun_msg2
        方法: POST
        参数:
            {
                r:{
                    group_uin           // gid
                    content             // 发送内容
                    msg_id              // 消息id, 每次发送消息应该递增
                    clientid            // 客户端id
                    psessionid          // sessionid
                }
                clientid
                psessionid
            }
        """
        gid = self.group_info.get(group_uin, {}).get("gid")
        source = content
        content = self.make_msg_content(source)

        url = "http://d.web2.qq.com/channel/send_qun_msg2"
        r = {"group_uin": gid, "content": content,
            "msg_id": self.msg_id, "clientid": self.clientid,
            "psessionid": self.psessionid}
        params = [("r", json.dumps(r)), ("psessionid", self.psessionid),
                ("clientid", self.clientid)]

        delay, n = self.get_delay(content)
        callback = self.send_group_msg_back


        self.http.post(url, params, headers = self.base_header,
                       callback = callback, args = (source, group_uin, n),
                       delay = delay)


    def get_delay(self, content):
        MIN = MESSAGE_INTERVAL
        delay = 0
        sub = time.time() - self.last_msg_time
        if self.last_msg_numbers < 0:
            self.last_msg_numbers = 0

        # 不足最小间隔就补足最小间隔
        if sub < MIN:
            delay = MIN
            logging.debug(u"间隔 %s 小于 %s, 设置延迟为%s", sub, MIN, delay)

        # 如果间隔是已有消息间隔的2倍, 则清除已有消息数
        #print "sub", sub, "n:", self.last_msg_numbers
        if self.last_msg_numbers > 0 and sub / (MIN * self.last_msg_numbers)> 1:
            self.last_msg_numbers = 0

        # 如果还有消息未发送, 则加上他们的间隔
        if self.last_msg_numbers > 0:
            delay += MIN * self.last_msg_numbers
            logging.info(u"有%s条消息未发送, 延迟为 %s", self.last_msg_numbers, delay)


        n = 1
        # 如果这条消息和上条消息一致, 保险起见再加上一个最小间隔
        if self.last_msg_content == content and sub < MIN:
            delay += MIN
            self.last_msg_numbers += 1
            n = 2

        self.last_msg_numbers += 1
        self.last_msg_content = content

        if delay:
            logging.info(u"有 {1} 个消息未投递将会在 {0} 秒后投递"
                         .format(delay, self.last_msg_numbers))
        # 返回消息累加个数, 在消息发送后减去相应的数目
        return delay, n


    def send_group_msg_back(self, content, group_uin, n, resp):
        logging.info(u"发送群消息 {0} 到 {1}".format(content, group_uin))
        self.last_msg_time = time.time()
        if self.last_msg_numbers > 0:
            self.last_msg_numbers -= n


    def set_signature(self, signature, password, callback):
        """ 设置QQ签名,
        可以通过发送好友消息设置签名, 消息应按照如下格式:
            设置签名:[密码]|[签名内容]    // 密码和签名内容不能包含分割符
        url: http://s.web2.qq.com/api/set_long_nick2
        method: POST
        params:
                r : {
                    nlk         // 签名内容
                    vfwebqq     // 登录时获取的cookie值
                }
        headers:
            Referer:http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1
        """
        if password != Set_Password:
            return callback(u"你没有权限这么做")

        logging.info(u"设置QQ签名 {0}".format(signature))

        url = "http://s.web2.qq.com/api/set_long_nick2"
        params = (("r", json.dumps({"nlk":signature, "vfwebqq":self.vfwebqq})),)
        headers = {"Origin":"http://s.web2.qq.com"}
        headers.update(self.base_header)

        def callback(resp):
            data = resp.body
            print data
            result = json.loads(data).get("retcode")
            if result == 0:
                callback(u"设置成功")
            else:
                callback(u"设置失败")
        self.http.post(url, params, headers = headers, callback = callback)


    def run(self):
        self.get_login_sig()
        self.http.start()


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
    os.chdir("/")
    os.umask(0)

    _fork(2)
    pp = os.path.join(path, "pid.pid")

    with open(pp, 'w') as f:
        f.write(str(os.getpid()))

    lp = os.path.join(path, "log.log")
    print "日志文件: ", lp
    lf = open(lp, 'a')
    os.dup2(lf.fileno(), sys.stdout.fileno())
    os.dup2(lf.fileno(), sys.stderr.fileno())
    callback(*args, **kwargs)

    def _exit():
        os.remove(pp)
        lf.close()

    atexit.register(_exit)



if __name__ == "__main__":
    from config import QQ, QQ_PWD

    def main():
        import sys
        webqq = WebQQ(QQ, QQ_PWD)
        retry = True
        try:
            webqq.run()
        except KeyboardInterrupt:
            retry = False
            print >>sys.stderr, "Exiting..."
        except SystemExit as e:
            if e.code in [2, 0, 1]:
                retry = False
        except:
            retry = True
            traceback.print_exc()
        finally:
            if retry:
                os.execv(sys.executable, [sys.executable] + sys.argv)

    main()

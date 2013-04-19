#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/19 09:49:56
#   Desc    :   WebQQ
#
import time
import json
import random
import logging
import urllib2
import tempfile

from hashlib import md5
from functools import partial
from http_stream import HTTPStream
from message_dispatch import MessageDispatch

logging.basicConfig(level = logging.DEBUG)

class WebQQ(object):
    def __init__(self, qid, pwd):
        self.qid = qid               # QQ 号
        self.__pwd = pwd             # QQ密码
        self.nickname = None         # 初始化QQ昵称
        self.http_stream = HTTPStream.instance()       # HTTP 流
        self.msg_dispatch = MessageDispatch(self)

        self.aid = 1003903                                    # aid 固定
        self.clientid = random.randrange(11111111, 99999999)  # 客户端id 随机固定
        self.msg_id = random.randrange(1111111, 99999999)     # 消息id, 随机初始化

        self.require_check = False   # 是否需要验证码
        self.poll_and_heart = False  # 开始拉取消息和心跳

        # 初始化WebQQ登录期间需要保存的数据
        self.check_code = None
        self.skey = None
        self.ptwebqq = None

        self.check_data = None       # 初始化检查时返回的数据
        self.blogin_data = None      # 初始化登录前返回的数据

        self.friend_info = {}        # 初始化好友列表
        self.group_info = {}         # 初始化组列表
        self.group_members_info = {} # 初始化组成员列表

        self.hb_time = int(time.time() * 1000)


    def handle_pwd(self, password):
        """ 根据检查返回结果,调用回调生成密码和保存验证码 """
        r, self._vcode, huin = eval("self." + self.check_data.rstrip(";"))
        pwd = md5(md5(password).digest() + huin).hexdigest().upper()
        return md5(pwd + self._vcode).hexdigest().upper()

    def ptui_checkVC(self, r, vcode, uin):
        """ 处理检查的回调 返回三个值 """
        if int(r) == 0:
            logging.info("Check Ok")
            self.check_code = vcode
        else:
            logging.warn("Check Error")
            self.check_code = self.get_check_img(vcode)
            self.require_check = True
        return r, self.check_code, uin

    def get_check_img(self, vcode):
        """ 获取验证图片 """
        url = "https://ssl.captcha.qq.com/getimage"
        params = [("aid", self.aid), ("r", random.random()),
                  ("uin", self.qid)]
        request = self.http_stream.make_get_request(url, params)
        cookie = urllib2.HTTPCookieProcessor(self.http_stream.cookiejar)
        opener = urllib2.build_opener(cookie)
        res = opener.open(request)
        path = tempfile.mktemp()
        fp = open(path, 'wb')
        fp.write(res.read())
        fp.close()
        print u"打开验证图片, 并输入验证码: {0}".format(path)
        check_code = ""
        while not check_code:
            check_code = raw_input("打开上面连接输出图片上的验证码: ")
        return check_code.strip().upper()


    def ptuiCB(self, scode, r, url, status, msg, nickname = None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        if int(scode) == 0:
            logging.info("Get ptwebqq Ok")
            self.skey = self.http_stream.cookie['.qq.com']['/']['skey'].value
            self.ptwebqq = self.http_stream.cookie['.qq.com']['/']['ptwebqq'].value
        else:
            logging.warn("Get ptwebqq Error")
        if nickname:
            self.nickname = nickname


    def get_group_member_nick(self, gcode, uin):
        return self.group_members_info.get(gcode, {}).get(uin, {}).get("nick")


    def check(self):
        """ 检查是否需要验证码
        url :
            http://check.ptlogin2.qq.com/check
        方法:   GET
        参数:
            {
                uin     // qq号
                appid   // 程序id 固定为1003903
                r       // 随机数
            }
        返回:
            ptui_checkVC('0','!PTH','\x00\x00\x00\x00\x64\x74\x8b\x05');
            第一个参数表示状态码, 0 不需要验证, 第二个为验证码, 第三个为uin
        """
        logging.info("Start check")
        url = "http://check.ptlogin2.qq.com/check"
        params = {"uin":self.qid, "appid":self.aid,
                  "r" : random.random()}
        request = self.http_stream.make_get_request(url, params)
        self.http_stream.add_request(request, self.before_login)


    def before_login(self, resp):
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
        然后获取Cookie里的ptwebqq,skey保存在实例里,供后面的接口调用
        """
        logging.info("check done, login...")
        self.check_data = resp.read().strip().rstrip(";")
        password = self.handle_pwd(self.__pwd)
        url = "https://ssl.ptlogin2.qq.com/login"
        params = [("u",self.qid), ("p",password), ("verifycode", self.check_code),
                  ("webqq_type",10), ("remember_uin", 1),("login2qq",1),
                  ("aid", self.aid), ("u1", "http://www.qq.com"), ("h", 1),
                  ("ptredirect", 0), ("ptlang", 2052), ("from_ui", 1),
                  ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                  ("mibao_css","m_webqq"), ("t",1), ("g",1), ("js_type",0),
                  ("js_ver", 10021)]
        request = self.http_stream.make_get_request(url, params)
        if self.require_check:
            request.add_header("Referer",  "https://ui.ptlogin2.qq.com/cgi-"
                            "bin/login?target=self&style=5&mibao_css=m_"
                            "webqq&appid=1003903&enable_qlogin=0&no_ver"
                            "ifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Fl"
                            "oginproxy.html&f_url=loginerroralert&stron"
                            "g_login=1&login_state=10&t=20130221001")
        return request, self.login


    def login(self, resp):
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
            续加上 Referer和 Origin 头:
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
        logging.info("login done, login2...")
        blogin_data = resp.read().decode("utf-8").strip().rstrip(";")
        eval("self." + blogin_data)

        url = "http://d.web2.qq.com/channel/login2"
        params = [("r", '{"status":"online","ptwebqq":"%s","passwd_sig":"",'
                '"clientid":"%d","psessionid":null}'\
                % (self.ptwebqq, self.clientid)),
                ("clientid", self.clientid),
                ("psessionid", "null")
                ]

        request = self.http_stream.make_post_request(url, params)

        request.add_header("Referer", "http://d.web2.qq.com/proxy.html?"
                           "v=20110331002&callback=1&id=3")
        request.add_header("Origin", "http://d.web2.qq.com")
        return request, self.update_friend


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

        data = json.loads(resp.read())
        if login:
            logging.info("login2 done")
            logging.info("update friend")
            self.psessionid = data.get("result", {}).get("psessionid")
            self.vfwebqq = data.get("result", {}).get("vfwebqq")
            url = "http://s.web2.qq.com/api/get_user_friends2"
            params = [("r", json.dumps({"h":"hello",
                                        "vfwebqq":self.vfwebqq}))]

            request = self.http_stream.make_post_request(url, params)
            request.add_header( "Referer",
                "http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1")

            read_back = partial(self.update_friend, login = False)
            return request, read_back
        else:
            logging.info("update friend done")
            lst = data.get("result", {}).get("info", [])
            for info in lst:
                uin = info.get("uin")
                self.friend_info[uin] = info
            self.update_group()
            url = "http://s.web2.qq.com/api/get_user_friends2"
            params = [("r", json.dumps({"h":"hello",
                                        "vfwebqq":self.vfwebqq}))]

            request = self.http_stream.make_post_request(url, params)
            request.add_header( "Referer",
                "http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1")

            read_back = partial(self.update_friend, login = False)
            return request, read_back, 300



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
        logging.info("fetch group list...")
        url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
        params = [("r", '{"vfwebqq":"%s"}' % self.vfwebqq),]
        request = self.http_stream.make_post_request(url, params)
        request.add_header("Origin", "http://s.web2.qq.com")
        request.add_header("Referer", "http://s.web2.qq.com/proxy.ht"
                                "ml?v=20110412001&callback=1&id=1")

        self.http_stream.add_request(request, self.group_members)

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
        logging.info("fetch group list done")
        logging.info("fetch group's members")
        data = json.loads(resp.read())
        group_list = data.get("result", {}).get("gnamelist", [])
        for i, group in enumerate(group_list):
            gcode = group.get("code")
            url = "http://s.web2.qq.com/api/get_group_info_ext2"
            params = [("gcode", gcode),("vfwebqq", self.vfwebqq),
                    ("t", int(time.time()))]
            request = self.http_stream.make_get_request(url, params)
            request.add_header( "Referer",
                "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3")
            read_back = self.do_group_members
            if i == len(group_list) -1 :
                read_back = partial(read_back, gcode = gcode, last = True)
            else:
                read_back = partial(read_back, gcode = gcode)
            self.http_stream.add_request(request, read_back)
            self.group_info[gcode] = group


    def do_group_members(self, resp, gcode, last = False):
        """ 获取群成员数据 """
        data = json.loads(resp.read())
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

        if last and not self.poll_and_heart:
            logging.info("fetch group's members done")
            self.poll()
            self.heartbeat()


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
        logging.info("start poll")

        if not self.poll_and_heart:
            self.poll_and_heart = True
        url = "http://d.web2.qq.com/channel/poll2"
        rdic = {"clientid": self.clientid, "psessionid": self.psessionid,
                "key": 0, "ids":[]}
        params = [("r", json.dumps(rdic)), ("clientid", self.clientid),
                ("psessionid", self.psessionid)]
        request = self.http_stream.make_post_request(url, params)
        request.add_header( "Referer", "http://d.web2.qq.com/proxy.html?v="
                            "20110331002&callback=1&id=2")

        read_back = partial(self.handle_msg, next_req = request)
        self.http_stream.add_request(request, read_back)


    def handle_msg(self, resp, next_req):
        """ 处理消息 """
        data = resp.read()
        try:
            msg = json.loads()
            logging.info("Got message {0!r}".format(msg))
            self.msg_dispatch.dispatch(msg)
        except ValueError:
            logging.error(u"Message can't loads: %s", data)

        return next_req, partial(self.handle_msg, next_req = next_req)


    def heartbeat(self):
        """ 开始心跳
        url:http://web.qq.com/web2/get_msg_tip
        方法: GET
        参数:
            {
                uin  // 固定为空
                tp   // 固定为1
                rc   // 固定为1
                lv   // 固定为2
                t    // 开始的心跳时间(int(time.time()) * 1000)
            }
        """
        logging.info("start heartbeat")
        if not self.poll_and_heart:
            self.poll_and_heart = True

        url = "http://web.qq.com/web2/get_msg_tip"
        params = [("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                    ("rc", 1), ("lv", 2),
                ("t", int(self.hb_time * 1000))]

        request = self.http_stream.make_get_request(url, params)
        read_back = partial(self.hb_next, next_req = request)
        self.http_stream.add_request(request, read_back)


    def hb_next(self, resp, next_req):
        """ 持续心跳 """
        logging.info("Heartbeat")
        return next_req, partial(self.hb_next, next_req = next_req), 60


    def make_msg_content(self, content):
        """ 构造QQ消息的内容 """
        return json.dumps([content, ["font", {"name":"Monospace", "size":10,
                                   "style":[0, 0, 0], "color":"000000"}]])


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

        content = self.make_msg_content(content)

        url = "http://d.web2.qq.com/channel/send_buddy_msg2"

        r = {"to":to_uin, "face":564, "content":content,
             "clientid":self.clientid, "msg_id": self.msg_id,
             "psessionid": self.psessionid}
        self.msg_id += 1
        params = [("r",json.dumps(r)), ("clientid",self.clientid),
                  ("psessionid", self.psessionid)]

        request = self.http_stream.make_post_request(url, params)
        request.add_header( "Referer",
            "http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3")
        request.add_header("Origin", "http://d.web2.qq.com")
        self.http_stream.add_request(request)


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
        gid = self.group_info.get(group_uin).get("gid")
        content = self.make_msg_content(content)

        url = "http://d.web2.qq.com/channel/send_qun_msg2"
        r = {"group_uin": gid, "content": content,
            "msg_id": self.msg_id, "clientid": self.clientid,
            "psessionid": self.psessionid}
        params = [("r", json.dumps(r)), ("sessionid", self.psessionid),
                ("clientid", self.clientid)]
        self.msg_id += 1

        request = self.http_stream.make_post_request(url, params)
        request.add_header("Referer",  "http://d.web2.qq.com/proxy.html")
        self.http_stream.add_request(request)


    def run(self):
        self.check()
        self.http_stream.start()


if __name__ == "__main__":
    from config import QQ, QQ_PWD
    webqq = WebQQ(QQ, QQ_PWD)
    webqq.run()

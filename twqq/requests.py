#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/11 18:21:10
#   Desc    :
#
import os
import re
import json
import time
import random
import inspect
import urllib2
import smtplib
import logging
import tempfile
import threading
import traceback

from hashlib import md5
from functools import partial
from email.mime.text import MIMEText

import _hash
import const
import config

from tornadohttpclient import UploadForm as Form

try:
    raw_input
except NameError:  #py3
    raw_input = input



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


    def send_notice_email(self):
        """ 发送提醒邮件
        """
        if not getattr(config, "SMTP_HOST", False):
            return False

        postfix = ".".join(config.SMTP_HOST.split(".")[1:])
        me = "bot<{0}@{1}>".format(config.SMTP_ACCOUNT, postfix)

        msg =  MIMEText(""" 你的WebQQ机器人需要一个验证码,
                    请打开你的服务器输入验证码:
                    http://{0}:{1}""".format(config.HTTP_LISTEN, config.HTTP_PORT),
                    _subtype="plain", _charset="utf-8")
        msg['Subject'] = u"WebQQ机器人需要验证码"
        msg["From"] = me
        msg['To'] = config.EMAIL
        try:
            server = smtplib.SMTP()
            server.connect(config.SMTP_HOST)
            server.login(config.SMTP_ACCOUNT, config.SMTP_PASSWORD)
            server.sendmail(me, [config.EMAIL], msg.as_string())
            server.close()
            return True
        except Exception, e:
            traceback.print_exc()
            return False


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
            logging.info("开始拉取信息和心跳")
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
        MIN = config.MESSAGE_INTERVAL
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
            logging.debug(resp.headers)
            if resp.headers.get("Content-Type") == "application/json":
                data = json.loads(data) if data else {}
            else:
                try:
                    data = json.loads(data)
                except:
                    pass
            if func:
                func(resp, data, *args, **kwargs)

            for f in get_request_callbacks(request):
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
                funcs = _handle_msg_funcs.get(m.get("poll_type"))
                [f(self, m) for f in funcs]


class WebQQRequest(object):
    METHOD_POST = "post"
    METHOD_GET = "get"

    hub = None
    url = None
    params = {}
    headers = {}
    method = METHOD_GET         # 默认请求为GET
    kwargs = {}
    ready = True

    def __init__(self, *args, **kwargs):
        self.delay = kwargs.pop("delay", 0)
        self.init(*args, **kwargs)


    def handle_exc(self, type, value, trace):
        pass



class LoginSigRequest(WebQQRequest):
    url = "https://ui.ptlogin2.qq.com/cgi-bin/login"

    def init(self):
        logging.info("获取 login_sig...")
        self.params = [("daid", self.hub.daid), ("target", "self"), ("style", 5),
                  ("mibao_css", "m_webqq"), ("appid", self.hub.aid),
                  ("enable_qlogin", 0), ("no_verifyimg", 1),
                  ("s_url", "http://web2.qq.com/loginproxy.html"),
                  ("f_url", "loginerroralert"),
                  ("strong_login", 1), ("login_state", 10),
                  ("t", "20130723001")]

    def callback(self, resp, data):
        sigs = self.hub.SIG_RE.findall(resp.body)
        if len(sigs) == 1:
            self.hub.login_sig = sigs[0]
            logging.info(u"获取Login Sig: {0}".format(self.hub.login_sig))
        else:
            logging.warn(u"没有获取到 Login Sig, 后续操作可能失败")

        self.hub.load_next_request(ChecRequest())


class ChecRequest(WebQQRequest):
    """ 检查是否需要验证码
    """
    url = "http://check.ptlogin2.qq.com/check"

    def init(self):
        self.params = {"uin":self.hub.qid, "appid":self.hub.aid,
                       "u1": const.CHECK_U1, "login_sig":self.hub.login_sig,
                       "js_ver":10040, "js_type":0, "r" : random.random()}
        self.headers.update({"Referer":const.CHECK_REFERER})


    def callback(self, resp, data):
        r, vcode, uin = eval("self.hub."+data.strip().rstrip(";"))
        logging.debug("R:{0} vcode:{1}".format(r, vcode))
        if int(r) == 0:
            logging.info("验证码检查完毕, 不需要验证码")
            password = self.hub.handle_pwd(r, vcode, uin)
            self.hub.check_code = vcode
            self.hub.clean()
            self.hub.load_next_request(BeforeLoginRequest(password))
        else:
            logging.warn("验证码检查完毕, 需要验证码")
            self.hub.require_check = True
            self.hub.load_next_request(CheckImageRequest(r, vcode, uin))


class CheckImageRequest(WebQQRequest):
    url = "https://ssl.captcha.qq.com/getimage"

    def init(self, r, vcode, uin):
        self.r, self.vcode, self.uin = r, vcode, uin
        self.params = [("aid", self.hub.aid), ("r", random.random()),
                       ("uin", self.hub.qid)]

    def callback(self, resp, data):
        self.hub.require_check_time = time.time()
        with open(self.hub.checkimg_path, 'wb') as f:
            f.write(resp.body)

        if getattr(config, "UPLOAD_CHECKIMG", False):
            logging.info(u"正在上传验证码...")
            res = self.hub.upload_file("check.jpg", self.hub.checkimg_path)
            logging.info(u"验证码已上传, 地址为: {0}".format(res.read()))

        if getattr(config, "HTTP_CHECKIMG", False):
            self.unlock()
            logging.info(u"已开启浏览器提交验证码, 地址为: http://{0}:{1}"
                         .format(getattr(config, "HTTP_LISTEN", "localhost"),
                                 getattr(config, "HTTP_PORT", "8000")))
            self.hub.setup_handler(self.r, self.vocde, self.uin,
                                   BeforeLoginRequest)
            if getattr(config, "EMAIL_NOTICE", False):
                if self.hub.send_notice_email():
                    logging.info(u"已成功发送邮件提醒")
                else:
                    logging.warn(u"发送邮件提醒失败")
        else:
            logging.info(u"验证码本地路径为: {0}".format(self.hub.checkimg_path))
            check_code = None
            while not check_code:
                check_code = raw_input("输入验证码: ")

            self.hub.check_code = check_code.strip().lower()
            pwd = self.hub.handle_pwd(self.r, self.hub.check_code.upper(), self.uin)
            self.hub.load_next_request(BeforeLoginRequest(pwd))


class BeforeLoginRequest(WebQQRequest):
    """ 登录前的准备
    """
    url = "https://ssl.ptlogin2.qq.com/login"
    def init(self, password):
        self.hub.lock()
        self.params = [("u",self.hub.qid), ("p",password),
                       ("verifycode", self.hub.check_code),
                       ("webqq_type",10), ("remember_uin", 1),("login2qq",1),
                       ("aid", self.hub.aid), ("u1", const.BLOGIN_U1),
                       ("h", 1), ("action", 4-5-8246), ("ptredirect", 0),
                       ("ptlang", 2052), ("from_ui", 1), ("daid", self.hub.daid),
                       ("pttype", 1), ("dumy", ""), ("fp", "loginerroralert"),
                       ("mibao_css","m_webqq"), ("t",1), ("g",1), ("js_type",0),
                       ("js_ver", 10040), ("login_sig", self.hub.login_sig)]
        referer =  const.BLOGIN_R_REFERER if self.hub.require_check else const.BLOGIN_REFERER
        self.headers.update({"Referer": referer})
        logging.info("检查完毕")

    def ptuiCB(self, scode, r, url, status, msg, nickname = None):
        """ 模拟JS登录之前的回调, 保存昵称 """
        if int(scode) == 0:
            logging.info("从Cookie中获取ptwebqq的值")
            old_value = self.hub.ptwebqq
            try:
                self.hub.ptwebqq = self.hub.client.http.cookie['.qq.com']['/']['ptwebqq'].value
            except:
                logging.error("从Cookie中获取ptwebqq的值失败, 使用旧值尝试")
                self.hub.ptwebqq = old_value
        elif int(scode) == 4:
            logging.error(msg)
            # TODO
            # if self.status_callback:
            #     self.status_callback(False, msg)
            # self.check()
        else:
            logging.error(u"server response: {0}".format(msg.decode('utf-8')))
            #TODO
            # self.check()

        if nickname:
            self.hub.nickname = nickname.decode('utf-8')

        return url

    def callback(self, resp, data):
        blogin_data = resp.body.decode("utf-8").strip().rstrip(";")
        url = eval("self." + blogin_data)
        self.hub.load_next_request(LoginRequest(url))


class LoginRequest(WebQQRequest):
    """ 登录前的准备
    """
    def init(self, url):
        logging.info("开始登录前准备...")
        self.url = url
        self.headers.update(Referer = const.LOGIN_REFERER)

    def callback(self, resp, data):
        self.hub.unlock()
        if os.path.exists(self.hub.checkimg_path):
            os.remove(self.hub.checkimg_path)

        self.hub.load_next_request(Login2Request())


class Login2Request(WebQQRequest):
    """ 真正的登录
    """
    url = "http://d.web2.qq.com/channel/login2"
    method = WebQQRequest.METHOD_POST

    def init(self):
        logging.info("准备完毕, 开始登录")
        self.headers.update(Referer = const.S_REFERER, Origin = const.D_ORIGIN)
        self.params = [("r", json.dumps({"status": "online",
                                         "ptwebqq": self.hub.ptwebqq,
                                         "passwd_sig":"",
                                         "clientid":self.hub.clientid,
                                         "psessionid":None})),
                       ("clientid", self.hub.clientid),
                       ("psessionid", "null")]

    def callback(self, resp, data):
        self.hub.require_check_time = None
        if not resp.body:
            logging.error(u"没有获取到数据, 登录失败")
            # if self.status_callback:
            #     self.status_callback(False, "登录失败 没有数据返回")
            #TODO return self.check()
            return

        if data.get("retcode") != 0:
            # TODO
            # if self.status_callback:
            #     self.status_callback(False, "登录失败 {0}".format(data))

            logging.error("登录失败 {0!r}".format(data))
            return
        self.hub.vfwebqq = data.get("result", {}).get("vfwebqq")
        self.hub.psessionid = data.get("result", {}).get("psessionid")
        logging.info("登录成功")

        if not config.DEBUG and not getattr(config, "HTTP_CHECKIMG", False):
            aw = ""
            while aw.lower() not in ["y", "yes", "n", "no"]:
                aw = raw_input("是否将程序至于后台[y] ")
                if not aw:
                    aw = "y"

            if aw in ["y", "yes"]:
                self.hub.run_daemon(FriendInfoRequest())
                return
        self.hub.load_next_request(FriendInfoRequest())


class FriendInfoRequest(WebQQRequest):
    """ 加载好友信息
    """
    url = "http://s.web2.qq.com/api/get_user_friends2"
    method = WebQQRequest.METHOD_POST

    def init(self):
        self.params = [("r", json.dumps({"h":"hello", "hash":self.hub._hash(),
                                    "vfwebqq":self.hub.vfwebqq}))]
        self.headers.update(Referer = const.S_REFERER)

    def callback(self, resp, data):
        # TODO
        # if not resp.body:
        #     if self.status_callback and call_status:
        #         self.status_callback(False, u"更新好友信息失败")
        #     return
        # if data.get("retcode") != 0 and call_status:
        #     self.status_callback(False, u"好友列表加载失败, 错误代码:{0}"
        #                             .format(data.get("retcode")))
        #     return

        lst = data.get("result", {}).get("info", [])
        for info in lst:
            uin = info.get("uin")
            self.hub.friend_info[uin] = info

        marknames = data.get("result", {}).get("marknames", [])
        [self.hub.mark_to_uin.update({minfo.get("markname"): minfo.get("uin")})
            for minfo in marknames]

        logging.debug("加载好友信息 {0!r}".format(self.hub.friend_info))
        logging.info(data)
        self.hub.load_next_request(GroupListRequest())
        self.hub.load_next_request(FriendInfoRequest(delay = 3600))
        # if self.status_callback and call_status:
        #     self.status_callback(True)


class GroupListRequest(WebQQRequest):
    """ 获取群列表
    """
    url = "http://s.web2.qq.com/api/get_group_name_list_mask2"
    method = WebQQRequest.METHOD_POST

    def init(self):
        self.params = {"r": json.dumps({"vfwebqq":self.hub.vfwebqq})}
        self.headers.update(Origin = const.S_ORIGIN)
        self.headers.update(Referer = const.S_REFERER )
        logging.info("获取群列表")


    def callback(self, resp, data):
        logging.debug(u"群信息 {0!r}".format(data))
        group_list = data.get("result", {}).get("gnamelist", [])
        logging.debug(u"群列表: {0!r}".format(group_list))
        if not group_list:
            self.hub.start_poll()

        for i, group in enumerate(group_list):
            gcode = group.get("code")
            self.hub.load_next_request(GroupMembersRequest(gcode, i == 0))
            self.hub.group_info[gcode] = group


class GroupMembersRequest(WebQQRequest):
    """ 获取群成员

    :param gcode: 群代码
    :param poll: 是否开始拉取信息和心跳
    :type poll: boolean
    """
    url = "http://s.web2.qq.com/api/get_group_info_ext2"
    def init(self, gcode, poll = False):
        self._poll = poll
        self._gcode = gcode
        self.params = [("gcode", gcode),("vfwebqq", self.hub.vfwebqq),
                       ("cb", "undefined"), ("t", int(time.time()))]
        self.headers.update(Referer = const.S_REFERER)


    def callback(self, resp, data):
        logging.debug(u"获取群成员信息 {0!r}".format(data))
        members = data.get("result", {}).get("minfo", [])
        self.hub.group_members_info[self._gcode] = {}
        for m in members:
            uin = m.get("uin")
            self.hub.group_members_info[self._gcode][uin] = m

        cards = data.get("result", {}).get("cards", [])

        for card in cards:
            uin = card.get("muin")
            group_name = card.get("card")
            self.hub.group_members_info[self._gcode][uin]["nick"] = group_name

        logging.debug(u"群成员信息: {0!r}".format(self.group_members_info))


        if self._poll:
            self.hub.start_poll()


class HeartbeatRequest(WebQQRequest):
    """ 心跳请求
    """
    url = "http://web.qq.com/web2/get_msg_tip"
    def init(self):
        self.params = dict([("uin", ""), ("tp", 1), ("id", 0), ("retype", 1),
                        ("rc", self.hub.rc), ("lv", 3), ("t", int(time.time() * 1000))])
        self.hub.rc += 1

    def callback(self, resp, data):
        logging.info("心跳...")


class PollMessageRequest(WebQQRequest):
    """ 拉取消息请求
    """
    url = "http://d.web2.qq.com/channel/poll2"
    method = WebQQRequest.METHOD_POST
    kwargs = {"request_timeout": 60.0, "connect_timeout": 60.0}

    def init(self):
        rdic = {"clientid": self.hub.clientid, "psessionid": self.hub.psessionid,
                "key": 0, "ids":[]}
        self.params = [("r", json.dumps(rdic)), ("clientid", self.hub.clientid),
                ("psessionid", self.hub.psessionid)]
        self.headers.update(Referer =  const.D_REFERER)
        self.headers.update(Origin = const.D_ORIGIN)


    def callback(self, resp, data):
        try:
            if data.get("retcode") in [121, 100006]:
                logging.error(u"获取消息异常 {0!r}".format(data))
                exit()
            logging.info(u"获取消息: {0!r}".format(data))
            # TODO
            self.hub.dispatch(data)
        except Exception as e:
            logging.error(u"消息获取异常: {0}".format(e))

        self.hub.load_next_request(PollMessageRequest())


class SessGroupSigRequest(WebQQRequest):
    """ 获取临时消息群签名请求

    :param to_uin: 临时消息接收人uin
    :param sess_reqeust: 发起临时消息的请求
    """

    url = "http://d.web2.qq.com/channel/get_c2cmsg_sig2"
    def init(self, to_uin, sess_reqeust):
        self.sess_request = sess_reqeust
        self.to_uin = to_uin
        self.params = (("id", 833193360), ("to_uin", to_uin),
                       ("service_type", 0), ("clientid", self.hub.clientid),
                       ("psessionid", self.hub.psessionid), ("t", time.time()))
        self.headers.update(Referer = const.S_REFERER)


    def callback(self, resp, data):
        result = data.get("result")
        group_sig = result.get("value")
        if data.get("retcode") != 0:
            logging.warn(u"加载临时消息签名失败: {0}".format(group_sig))
            return

        logging.info(u"加载临时消息签名 {0} for {1}".format(group_sig, self.to_uin))
        self.group_sig[self.to_uin] = group_sig
        self.sess_request.ready = True
        self.sess_request.init_params(group_sig)
        self.hub.load_next_request(self.sess_request)


class SessMsgRequest(WebQQRequest):
    """ 发送临时消息请求

    :param to_uin: 接收人 uin
    :param content: 发送内容
    """
    url = "http://d.web2.qq.com/channel/send_sess_msg2"
    method = WebQQRequest.METHOD_POST
    def init(self, to_uin, content):
        self.to = to_uin
        self._content = content
        self.content = self.hub.make_msg_content(content)
        group_sig = self.hub.group_sig.get(to_uin)
        if not group_sig:
            self.ready = False
            self.hub.load_next_request(SessGroupSigRequest(to_uin, self))
        else:
            self.init_params(group_sig)


    def init_params(self, group_sig):
        self.delay, self.number = self.hub.get_delay(self._content)
        self.params = (("r", json.dumps({"to":self.to, "group_sig":group_sig,
                                    "face":564, "content":self.content,
                                    "msg_id": self.hub.msg_id, "service_type":0,
                                    "clientid":self.hub.clientid,
                                    "psessionid":self.hub.psessionid})),
                  ("clientid", self.hub.clientid), ("psessionid", self.hub.psessionid))


    def callback(self, resp, data):
        logging.info(u"发送给 {0} 临时消息成功".format(self.to))
        self.hub.consume_delay(self.number)


class GroupMsgRequest(WebQQRequest):
    """ 发送群消息

    :param group_uin: 群uin
    :param content: 消息内容
    """
    url = "http://d.web2.qq.com/channel/send_qun_msg2"
    method = WebQQRequest.METHOD_POST
    def init(self, group_uin, content):
        self.delay, self.number = self.get_delay(content)
        self.gid = self.hub.get_group_id(group_uin)
        self.group_uin = group_uin
        self.source = content
        content = self.hub.make_msg_content(content)
        r = {"group_uin": self.gid, "content": content,
            "msg_id": self.hub.msg_id, "clientid": self.hub.clientid,
            "psessionid": self.hub.psessionid}
        self.params = [("r", json.dumps(r)), ("psessionid", self.hub.psessionid),
                ("clientid", self.hub.clientid)]
        self.headers.update(Origin = const.D_ORIGIN,
                            Referer = const.D_REFERER)

    def callback(self, resp, data):
        logging.info(u"发送群消息 {0} 到 {1} 成功"
                     .format(self.source, self.group_uin))
        self.hub.consume_delay(self.number)


class BuddyMsgRequest(WebQQRequest):
    """ 好友消息请求

    :param to_uin: 消息接收人
    :param content: 消息内容
    :param callback: 消息发送成功的回调
    """
    url = "http://d.web2.qq.com/channel/send_buddy_msg2"
    method = WebQQRequest.METHOD_POST
    def init(self, to_uin, content, callback = None):
        self.to_uin = to_uin
        self.source = content
        self._callback = callback
        self.content = self.make_msg_content(content)
        r = {"to":to_uin, "face":564, "content":content,
             "clientid":self.hub.clientid, "msg_id": self.hub.msg_id,
             "psessionid": self.hub.psessionid}
        self.params = [("r",json.dumps(r)), ("clientid",self.hub.clientid),
                  ("psessionid", self.hub.psessionid)]
        self.headers.update(Origin = const.D_ORIGIN)
        self.headers.update(Referer = const.S_REFERER)

        self.delay, self.number = self.hub.get_delay(content)

    def callback(self):
        logging.info(u"发送好友消息 {0} 给 {1} 成功"
                     .format(self.source, self.to_uin))
        if self._callback:
            self._callback(True)

        self.hub.consume_delay(self.number)


class SetSignatureRequest(WebQQRequest):
    """ 设置个性签名请求

    :param signature: 签名内容
    """
    url = "http://s.web2.qq.com/api/set_long_nick2"
    method = WebQQRequest.METHOD_POST
    def init(self, signature):
        self.params = (("r", json.dumps({"nlk":signature, "vfwebqq":self.hub.vfwebqq})),)
        self.headers.update(Origin = const.S_ORIGIN)
        self.headers.update(Referer = const.S_REFERER)


    def callback(self, resp, data):
        logging.info(u"设置签名成功")


class AcceptAddedRequest(WebQQRequest):
    """ 同意好友添加请求

    :param uin: 请求人uin
    :param qq_num: 请求人QQ号
    """
    url = "http://s.web2.qq.com/api/allow_and_add2"
    method = WebQQRequest.METHOD_POST

    def init(self, uin, qq_num):
        self.uin = uin
        self.qq_num = qq_num
        self.params = [("r","{\"account\":%d, \"gid\":0, \"mname\":\"%d\","
                    " \"vfwebqq\":\"%s\"}" % (qq_num, qq_num, self.hub.vfwebqq)),]
        self.headers.update(Origin = const.S_ORIGIN)
        self.headers.update(Referer = const.S_REFERER)


    def callback(self, resp, data):
        if data.get("retcode") == 0:
            logging.info(u"添加 {0} 成功".format(self.qq_num))
            self.hub.mark_to_uin[self.uin] = self.qq_num
        else:
            logging.info(u"添加 {0} 失败".format(self.qq_num))


FirstRequest = LoginSigRequest


_handle_msg_funcs = {}

def append_handler_msg_func(key, func):
    if _handle_msg_funcs.has_key(key):
        _handle_msg_funcs[key].append(func)
    else:
        _handle_msg_funcs[key] = [func]


def register_message_handler(typ):
    def wrap(func):
        append_handler_msg_func(typ, func)
        return func
    return wrap


def group_message_handler(func):
    """ 装饰处理群消息的函数

    处理函数应接收5个参数:

        nickname        发送消息的群昵称
        content         消息内容
        group_code      群代码
        from_uin        发送人的uin
        source          消息原包
    """
    @register_message_handler("group_message")
    def wrap(self, message):
        value = message.get("value", {})
        gcode = value.get("group_code")
        uin = value.get("send_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(contents)
        uname = self.get_group_member_nick(gcode, uin)
        return  func(uname, content, gcode, uin, message)

    return wrap


def buddy_message_handler(func):
    """ 装饰处理好友消息的函数

    处理函数应接收3个参数:

        from_uin         发送人uin
        content          消息内容
        source           消息原包
    """
    @register_message_handler("message")
    def wrap(self, message, *args, **kwargs):
        value = message.get("value", {})
        from_uin = value.get("from_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(contents)
        return func(from_uin, content, message, *args, **kwargs)

    return wrap


def kick_message_handler(func):
    """ 装饰处理下线消息的函数

    处理函数应接收1个参数:

        source      消息原包
    """
    @register_message_handler("kick_message")
    def wrap(self, message):
        return func(message)
    return wrap


def sess_message_handler(func):
    """ 装饰处理临时消息的函数

    处理函数应接收3个参数:

        from_uin        发送人uin
        content         消息内容
        source          消息原包
    """
    @register_message_handler("sess_message")
    def wrap(self, message):
        value = message.get("value", {})
        from_uin = value.get("from_uin")
        contents = value.get("content", [])
        content = self.handle_qq_msg_contents(contents)
        return func(from_uin, content, message)

    return wrap


def system_message_handler(func):
    """ 装饰处理系统消息的函数

    处理函数应接手4个参数:

        type        消息类型
        from_uin    产生消息的人的uin
        account     产生消息的人的qq号
        source      消息原包
    """
    @register_message_handler("system_message")
    def wrap(self, message):
        value = message.get('value')
        return func(value.get("type"), value.get("from_uin"),
                    value.get("account"), message)
    return wrap


_request_callbacks = {}

def check_request(request):
    """ 检查Request参数是否合法, 并返回一个类对象
    """
    if inspect.isclass(request):
        if not issubclass(request, WebQQRequest):
            raise ValueError("Request must be a subclass of WebQQRequest")
    elif isinstance(request, WebQQRequest):
        request = request.__class__
    else:
        raise ValueError("Request must be a subclass or instance of WebQQRequest")

    return request


def register_request_callback(request):
    """ 返回一个装饰器, 用于装饰函数,注册为Request的处理函数
    处理函数需接收两个参数:

        response        相应 ~tornado.httpclient.HTTPResponse instance
        data            response.body or dict

    :param request: 请求类或请求实例
    :type request: WebQQRequest or WebQQRequest instance
    :rtype: decorator function
    """
    request = check_request(request)

    def wrap(func):
        if _request_callbacks.has_key(request):
            _request_callbacks[request].append(func)
        else:
            _request_callbacks[request] = [func]
        return func
    return wrap

def get_request_callbacks(request):
    request = check_request(request)
    return _request_callbacks.get(request, [])

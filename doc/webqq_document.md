# WebQQ 协议分析文档

## 登录流程

::

            检查是否需要验证码
              /         \
             /           \
            需要       不需要
            /             \
           /               \
        获取验证码       使用返回js函数的三个参数结合密码生成加密密码
        (注意保存Cookie)     /                 /
          |                 /                 /
          |                /                 /
    使用验证码替代js函数的第二个参数        /
                                           /
                   +-----------------------
                   |
                校验密码
                   |
                   |
            请求上步所返回的连接
                   |
                   |
                  登录
                   |
                   |
            开始心跳和消息拉取


## 检查是否需要验证码
url

        https://ssl.ptlogin2.qq.com/check
方法

    GET

参数

            {
                uin     // qq号
                appid   // 程序id 固定为1003903
                r       // 随机数
                u1      // http://web2.qq.com/loginproxy.html
                js_ver  // 10040
                js_type // 0
            }

请求头:

    Referer: https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&style=5&mibao_css=m_webqq&appid=1003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb2.q

返回

            ptui_checkVC('0','!PTH','\x00\x00\x00\x00\x64\x74\x8b\x05');
            第一个参数表示状态码, 0 不需要验证, 第二个为验证码, 第三个为uin

## 获取验证码
url 

    https://ssl.captcha.qq.com/getimage

方法
    
    GET

参数

    aid    固定为1003903
    r      随机数
    uin    QQ号

返回

    验证码图片


## 校验密码
url:

    https://ssl.ptlogin2.qq.com/login

方法:

    GET
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

请求头

不需要验证码:

    Referer: https://ui.ptlogin2.qq.com/cgi-bin/login?target=self&style=5&mibao_css=mwebqq&appid=1003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Floginproxy.html&f_url=loginerroralert&strong_login=1&login_state=10&t=20130221001

需要验证码

    Referer : https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&style=5&mibao_css=m_webqq&appid=1003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb2.qq.com%2Floginproxy.html&f_url=loginerroralert&strong_login=1&login_state=10&t=20130903001

其他:

            如果check步骤验证了需要验证码, 需加上 Referer头 值为:
            https://ui.ptlogin2.qq.com/cgi-bin/login?target=self&style=5&mibao_css=m_webqq&appid=1003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb.qq.com%2Floginproxy.html&f_url=loginerroralert&strong_login=1&login_state=10&t=20130221001

接口返回:

    ptuiCB('0','0','http://www.qq.com','0','登录成功!', 'nickname');
    先检查是否需要验证码,不需要验证码则首先执行一次登录
    然后获取Cookie里的ptwebqq保存在实例里,供后面的接口调用


## 请求校验密码所返回的连接

url:
    
    校验密码所返回的的js函数的第三个参数
>ptuiCB('0','0','http://www.qq.com','0','登录成功!', 'nickname');

方法
    
    GET

请求头

    Referer: https://ui.ptlogin2.qq.com/cgi-bin/login?daid=164&target=self&style=5&mibao_css=m_webqq&appid=1003903&enable_qlogin=0&no_verifyimg=1&s_url=http%3A%2F%2Fweb2.qq.com%2Floginproxy.html&f_url=loginerroralert&strong_login=1&login_state=10&t=20130723001


## 登录
url:

    http://d.web2.qq.com/channel/login2

方法:

    POST
参数:

    r : {
        status       登录后的状态 ("online")
        ptwebqq      上次请求返回的cookie
        passwd_sig   固定为空
        clientid     随机的clientid
        psessionid   传递 null
    }
    clientid     客户端id
    psessionid   传递null

其他:

    需加上 Referer和 Origin 头:
    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3
    "Origin": "http://d.web2.qq.com"

返回:

    {u'retcode': 0,
    u'result': {
        'status': 'online', 'index': 1075,
        'psessionid': '', u'user_state': 0, u'f': 0,
        u'uin': 1685359365, u'cip': 3673277226,
        u'vfwebqq': u'', u'port': 43332}}
    保存result中的psessionid和vfwebqq供后面接口调用


## 更新好友列表
URL:

    http://s.web2.qq.com/api/get_user_friends2
METHOD:

    POST
PARAMS:

    r:{"h":"hello"
    "vfwebqq": vfwebqq  上一步返回
    hash     qq号 + vfwebqq 的hash值
    }
HEADER:

    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3

## 获取群列表:
url:

    http://s.web2.qq.com/api/get_group_name_list_mask2
method:

    POST
params:

    r : {
        vfwebqq     // 登录前返回的cookie值
    }

headers:

    Origin: http://s.web2.qq.com
    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3


## 获取群中的成员
url:

    http://s.web2.qq.com/api/get_group_info_ext2
method: 

    GET
params:

    gcode            群代码
    vfwebqq          登录前的cookie值
    t                int(time.time())

headers:

    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3


## 获取消息
url:

    http://d.web2.qq.com/channel/poll2
方法: 

    POST
参数:

    r:{
        clientid        客户端id
        psessionid      session id
        key             固定为0
        ids             固定为 []
    }
    clientid
    psessionid

头部:

    Referer: http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=2


## 心跳
url:

    http://web.qq.com/web2/get_msg_tip
方法:

    GET
参数:

    uin   固定为空
    tp    固定为1
    rc    固定为1
    id    固定位0
    lv    固定为2
    t     开始的心跳时间(int(time.time()) * 1000)

## 获取临时消息群签名
发送临时消息需要一个群签名
URL:

    http://d.web2.qq.com/channel/get_c2cmsg_sig2
METHOD:

    GET
PARAMS:

    id        请求ID 固定为833193360
    to_uin    消息接受人uin( 消息的from_uin)
    service_type    固定为0
    clientid        客户端id
    psessionid      session id
    t               当前时间秒1370671760656
HEADERS:

    Referer:http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=3

## 发送临时消息
URL:

    http://d.web2.qq.com/channel/send_sess_msg2
METHOD:

    POST
PARAMS:

    r:{
        to               消息接收人 uin
        group_sig        群签名
        face             固定为 564,
        content          发送内容
        msg_id           消息id
        service_type     固定为0,
        clientid         客户端id
        psessionid       sessionid
        }
    clientid             客户端id
    psessionid           sessionid
Headers:

    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3


## 发送好友消息
URL:

    http://d.web2.qq.com/channel/send_buddy_msg2

METHOD:

    POST

PARAMS:

    "r":{
        "to"             好友uin
        "face"           固定为564
        "content"        发送内容
        "msg_id"         消息id, 每发一条递增
        "clientid"       客户端id
        "psessionid"     sessionid
        }
    "clientid":clientid,
    "psessionid": psessionid,

HEADERS:

    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3

## 发送群消息
url:

    http://d.web2.qq.com/channel/send_qun_msg2
方法:

    POST
参数:

    r:{
        group_uin           // gid
        content             // 发送内容
        msg_id              // 消息id, 每次发送消息应该递增
        clientid            // 客户端id
        psessionid          // sessionid
    }
    clientid
    psessionid

请求头:

    Origin": http://d.web2.qq.com
    Referer:http://d.web2.qq.com/proxy.html?v=20110331002&callback=1&id=2

## 设置QQ签名,
url:

    http://s.web2.qq.com/api/set_long_nick2
method: 

    POST
params:

    r : {
        nlk         // 签名内容
        vfwebqq     // 登录时获取的cookie值
    }
headers:

    Referer:http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=1


## 确认添加好友请求

url:

    http://s.web2.qq.com/api/allow_and_add2

params:

    r: {
        account   // qqhao
        gid       // 固定为0
        mname     // 备注名
        vfwebqq
    }


headers:

    Origin: http://s.web2.qq.com
    Referer: http://s.web2.qq.com/proxy.html?v=20110412001&callback=1&id=3


# pual_bot 一个弱智的QQ机器人
pual_bot是一套建立在`Tornado`上的高效的支持并发的WebQQ机器人, 其主要功能有 执行Python代码, 贴代码, 英汉互译

# 测试QQ
~~我在VPS上跑了一个测试的, 大家可以把这个号拉进群里进行调戏`1685359365`~~

# 安装配置
程序依赖tornado, 可使用 easy_install 安装
```bash
easy_install pycurl tornado tornadohttpclient
```

将`config.py.example`重命名为 `config.py`, 填入QQ号码和密码配置, 执行webqq.py脚本. 

# 最近更新

## 2013-11-04

* 增加一个HTTP server用来通过浏览器输入验证码(配置见 ``config.py.example``)
* 增加当需要验证码时发送邮件提醒(配置见 ``config.py.example``)

# TODO
* 修复群成员列表获取
* 修复临时消息

如果您觉得功能不错, 您可以 [![捐赠](https://img.alipay.com/sys/personalprod/style/mc/btn-index.png)](http://me.alipay.com/woodd)让我更多的支持开源事业

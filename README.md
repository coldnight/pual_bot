# pual_bot 一个弱智的QQ机器人
pual_bot 是基于[twqq](https://github.com/coldnight/twqq)的高效的支持并发的WebQQ机器人, 其主要功能有 执行Python代码, 贴代码, 英汉互译

# 测试QQ
~~我在VPS上跑了一个测试的, 大家可以把这个号拉进群里进行调戏`1685359365`~~

# 安装配置
程序依赖 可使用 easy_install 安装
```bash
easy_install twqq http-parser regex
```

有些插件依赖于 bs4, 所以可以通过 apt 安装
```bash
sudo apt-get install python-bs4
```

将`config.py.example`重命名为 `config.py`, 填入QQ号码和密码配置, 执行webqq.py脚本. 

```bash
    mv doc/config.py.example config.py
```

# 最近更新
## 2014-06-25
* 插件优先级机制
* 更新添加插件
* 更新 Simsimi 接口

## 2014-03-05
* 增加讨论组支持

## 2014-01-16
* 增加插件机制
* 更改原先的消息处理机制, 使用插件机制来处理消息

## 2013-11-27
* 在遇到踢出时首先尝试重新登录(需更新 ``twqq`` 包)

## 2013-11-15
* 将WebQQ协议提取成一个包: https://github.com/coldnight/twqq
* 对代码进行重构


# TODO
* ~~修复群成员列表获取~~
* ~~修复临时消息~~
* ~~对代码重构~~
* ~~提取文档~~
* ~~去除废弃代码~~
* ~~将代码提取出一个包~~

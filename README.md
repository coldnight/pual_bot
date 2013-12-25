# pual_bot 一个弱智的QQ机器人
pual_bot 是基于[twqq](https://github.com/coldnight/twqq)的高效的支持并发的WebQQ机器人, 其主要功能有 执行Python代码, 贴代码, 英汉互译

# 测试QQ
~~我在VPS上跑了一个测试的, 大家可以把这个号拉进群里进行调戏`1685359365`~~

# 安装配置
程序依赖 可使用 easy_install 安装
```bash
easy_install twqq
```

将`config.py.example`重命名为 `config.py`, 填入QQ号码和密码配置, 执行webqq.py脚本. 

```bash
    mv doc/config.py.example twqq/config.py
```

# 最近更新
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

# pual_bot 一个弱智的QQ机器人
pual_bot是一套建立在`Tornado`上的高效的支持并发的WebQQ机器人, 其主要功能有 执行Python代码, 贴代码, 英汉互译

# 测试QQ
我在VPS上跑了一个测试的, 大家可以把这个号拉进群里进行调戏`1685359365`

# 安装配置
程序依赖tornado, 可使用 easy_install 安装
```bash
easy_install tornado lxml
```

将`config.py.example`重命名为 `config.py`, 填入QQ号码和密码配置, 执行webqq.py脚本. 

# 更新
* 放弃原先的 pyxmpp2 mainloop 改为tornado
* 不在将验证图片放到网站上, 而是作为临时文件保存, 请使用图片查看器查看, 然后输入验证码

## 2013-04-26
* 解决 在线时间稍长, 当经过多次请求后会触发`socket.gaierror(-2, 'Name or service not known')` 异常

## 2013-04-28
* 发送群消息频率过快导致的消息丢失

## 2013-5-10
* 使用开启子进程来解决无重试机制
* 使用延迟发送解决快速发送两条相同的内容的消息导致的丢是消息
* 增加`UPLOAD_CHECKIMG`选项用来支持选择是否将验证图片上传到图片服务器

## 2013-05-13
* 添加获取url标题功能

## 2013-05-16
* 添加Python shell功能, 可给每个人分配一个命名空间, 可以互动执行语句, 保持历史语句结果供下次使用

## 2013-05-29
* 添加SimSimi聊天机器人, 发送`Pual`打头的信息将会和`Simsimi`机器人互动

## 2013-06-04
* SimSimi容错, 去掉错误显示
* 支持`Pual`打头或结尾的消息, 不群分大小写

## 2013-06-06
* 防止SimSimi被封ip, SimSimi支持代理, 推荐goagent, 配置参见`config.py.example`
* 对`HTTPStream`进行重构
* 支持 socket.timeout 重试

## 2013-06-07
* 修复回应好友消息丢消息的情况
* 修复好友消息互动和命令不用加机器人昵称前缀或后缀

如果您觉得功能不错, 您可以 [![捐赠](https://img.alipay.com/sys/personalprod/style/mc/btn-index.png)](http://me.alipay.com/woodd)让我更多的支持开源事业

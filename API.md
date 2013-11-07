WebQQ发送消息接口

# 检查

接口

    /api/check

参数

    无

返回

    格式: json

    {
        status   状态             // False为验证码过期需等待
        requrie  是否需要验证吗
        message  消息
    }


# 提交验证码

接口

    /api/input

参数

    vertify        验证码

返回

    格式: json

    {
        status // 状态  True 成功登录 False登录失败
        message // 消息
    }



# 发送消息

接口

    /api/send

参数

    markname           备注名
    message            消息

返回

    格式: json

    {
        status      // 状态 True 发送成功, False 发送失败
        message     // 消息
    }

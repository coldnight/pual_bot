#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   Wood.D Wong
#   E-mail  :   wh_linux@126.com
#   Date    :   13/04/02 15:31:15
#   Desc    :   程序接口
#
from webqq.webqq import WebQQ

if __name__ == "__main__":
    QQ = 1685359365
    QQ_PWD = "4esz$ESZ"
    webqq = WebQQ(QQ, QQ_PWD)
    webqq.run()

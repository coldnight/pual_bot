#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/07 13:49:42
#   Desc    :
#

""" 这个函数翻译自Javascript

源在这里: http://pidginlwqq.sinaapp.com/hash.js

如果无法正常获取好友列表, 请查看上面js是否有更新, 有则更新本函数
"""

def webqq_hash(i, a):
    class b:
        def __init__(self, _b, i):
            self.s = _b or 0
            self.e = i or 0

    r = [i >> 24 & 255, i >> 16 & 255, i >> 8 & 255, i & 255]

    j = [ord(_a) for _a in a]

    e = [b(0, len(j) - 1)]
    while len(e) > 0:
        c = e.pop()
        if not (c.s >= c.e or c.s < 0 or c.e > len(j)):
            if c.s+1 == c.e:
                if (j[c.s] > j[c.e]) :
                    l = j[c.s]
                    j[c.s] = j[c.e]
                    j[c.e] = l
            else:
                l = c.s
                J = c.e
                f=j[c.s]
                while c.s < c.e:
                    while c.s < c.e and j[c.e]>=f:
                        c.e -= 1
                        r[0] = r[0] + 3&255

                    if c.s < c.e:
                        j[c.s] = j[c.e]
                        c.s += 1
                        r[1] = r[1] * 13 + 43 & 255

                    while c.s < c.e and j[c.s] <= f:
                        c.s += 1
                        r[2] = r[2] - 3 & 255

                    if c.s < c.e:
                        j[c.e] = j[c.s]
                        c.e -= 1
                        r[3] = (r[0] ^ r[1]^r[2]^r[3]+1) & 255
                j[c.s] = f
                e.append(b(l, c.s-1))
                e.append(b(c.s + 1, J))
    j = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "A",
         "B", "C", "D", "E", "F"]
    e = ""
    for c in range(len(r)):
        e += j[r[c]>>4&15]
        e += j[r[c]&15]

    return e

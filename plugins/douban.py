#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/20 10:33:47
#   Desc    :   爬取豆瓣书籍/电影/歌曲信息
#
from bs4 import BeautifulSoup

try:
    from plugins import BasePlugin
except:
    BasePlugin = object

class DoubanReader(object):
    def __init__(self, http):
        self.http = http
        self.url = "http://www.douban.com/search"

    def search(self, name, callback):
        params = {"q":name.encode("utf-8")}
        self.http.get(self.url, params, callback = self.parse_html,
                      kwargs = {"callback":callback})

    def parse_html(self, response, callback):
        soup = BeautifulSoup(response.body)
        item = soup.find(attrs = {"class":"content"})
        if item:
            try:
                type = item.find("span").text
                a = item.find('a')
                name = a.text
                href = a.attrs["href"]
                rating = item.find(attrs = {"class":"rating_nums"}).text
                cast = item.find(attrs={"class":"subject-cast"}).text
                desc = item.find("p").text
            except AttributeError:
                callback(u"没有找到相关信息")
                return

            if type == u"[电影]":
                cast_des = u"原名/导演/主演/年份" if len(cast.split("/")) == 4\
                        else u"导演/主演/年份"
            elif type == u"[书籍]":
                cast_des = u"作者/译者/出版社/年份" if len(cast.split("/")) == 4\
                        else u"作者/出版社/年份"
            body = u"{0}{1}:\n"\
                    u"评分: {2}\n"\
                    u"{3}: {4}\n"\
                    u"描述: {5}\n"\
                    u"详细信息: {6}\n"\
                    .format(type, name, rating, cast_des, cast, desc, href)
        else:
            body = u"没有找到相关信息"

        callback(body)


class DoubanPlugin(BasePlugin):
    douban = None
    def is_match(self, from_uin, content, type):
        if (content.startswith("<") and content.endswith(">")) or\
           (content.startswith(u"《") and content.endswith(u"》")):
            self._name = content.strip("<").strip(">").strip(u"《")\
                    .strip(u"》")

            if not self._name.strip():
                return False

            if self.douban is None:
                self.douban = DoubanReader(self.http)
            return True
        return False


    def handle_message(self, callback):
        self.douban.search(self._name, callback)

if __name__ == "__main__":
    from tornadohttpclient import TornadoHTTPClient
    def cb(b):
        print b
    douban = DoubanReader(TornadoHTTPClient())
    douban.search(u"百年孤独", cb)
    douban.search(u"鸟哥的私房菜", cb)
    douban.search(u"论语", cb)
    douban.search(u"寒战", cb)
    douban.search(u"阿凡达", cb)
    douban.search(u"创战记", cb)
    douban.search(u"简单爱", cb)
    TornadoHTTPClient().start()

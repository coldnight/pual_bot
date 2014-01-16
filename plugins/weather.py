#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 15:59:20
#   Desc    :   天气
#
""" 代码贡献自 EricTang (汤勺), 由 cold 整理
"""

from xml.dom.minidom import parseString

from plugins import BasePlugin

#weather service url address
WEATHER_URL = 'http://www.webxml.com.cn/webservices/weatherwebservice.asmx/getWeatherbyCityName'

class WeatherPlugin(BasePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith("-w"):
            self.city = content.split(" ")[1]
            self._format = u"\n {0}" if type == "g" else u"{0}"
            return True
        return False


    def handle_message(self, callback):
        self.get_weather(self.city, callback)

    def get_weather(self, city, callback):
        """
        根据城市获取天气
        """
        if city:
            params = {"theCityName":city.encode("utf-8")}
            self.http.get(WEATHER_URL, params, callback = self.callback,
                          kwargs = {"callback":callback})
        else:
            callback(self._format.foramt(u"缺少城市参数"))

    def callback(self, resp, callback):
        #解析body体
        document = ""
        for line in resp.body.split("\n"):
            document = document + line

        dom = parseString(document)

        strings = dom.getElementsByTagName("string")

        temperature_of_today = self.getText(strings[5].childNodes)
        weather_of_today = self.getText(strings[6].childNodes)

        temperature_of_tomorrow = self.getText(strings[12].childNodes)
        weather_of_tomorrow = self.getText(strings[13].childNodes)

        weatherStr = u"今明两天%s的天气状况是: %s %s ; %s %s;" % \
                (self.city, weather_of_today, temperature_of_today,
                 weather_of_tomorrow, temperature_of_tomorrow)

        callback(self._format.format(weatherStr))


    def getText(self, nodelist):
        """
        获取所有的string字符串string标签对应的文字
        """
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc


#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 16:15:59
#   Desc    :   PM2.5 查询插件
#
""" 代码贡献自 EricTang (汤勺), 由 cold 整理
"""
from ._pinyin import PinYin
from pyquery import PyQuery as pq

from plugins import BasePlugin


PM25_URL = 'http://www.pm25.in/'


class PM25Plugin(BasePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith("-pm25"):
            self.city = content.split(" ")[1]
            self._format = u"\n {0}" if type == "g" else u"{0}"
            return True
        return False

    def handle_message(self, callback):
        self.getPM25_by_city(self.convert2pinyin(self.city), callback)

    def getPM25_by_city(self, city, callback):
        """
        根据城市查询PM25值
        """
        self._city = city
        if city:
            url = PM25_URL + city.encode("utf-8")
            self.http.get(url, callback=self.callback,
                          kwargs={"callback": callback})
        else:
            callback(u'没输入城市你让我查个头啊...')

    def callback(self, resp, callback):
        html_doc = resp.body.decode('utf-8')
        q = pq(html_doc)
        # 获取城市名
        city_name = q('h2').text()
        if not city_name:
            return ''

        # 获取城市空气质量
        city_aqi = q('h4').text()

        # 获取数据更新时间
        city_aqi_update_time = q('.live_data_time')('p').text()

        # 获取城市各项指标的数据值
        city_air_data_array = q('.span12.data').text().split()[1:-1]
        a = iter(city_air_data_array)
        city_air_data = u'\n'.join([u'\t\t\t'.join(reversed(j))
                                   for j in zip(a, a)])
        city_air_status_str = u"当前查询城市为：{0}，空气质量为：{1}\n{2}\n"\
            u"{3}\n点击链接查看完整空气质量报告:{4}{5}"\
            .format(city_name, city_aqi, city_air_data,
                    city_aqi_update_time, PM25_URL, self._city)

        callback(city_air_status_str)

    def convert2pinyin(self, words):
        """
        将中文转换为拼音
        """
        if words:
            if u'\u4E00' < words[0] < u'\u9FBF':
                pinyin = PinYin()
                pinyin.load_word()
                pinyin_array = pinyin.hanzi2pinyin(string=words)
                return "".join(pinyin_array)
            else:
                return words
        else:
            return ''

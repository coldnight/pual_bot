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
from bs4 import BeautifulSoup

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
        if city:
            url = PM25_URL + city.encode("utf-8")
            self.http.get(url, callback = self.callback,
                          kwargs = {"callback":callback})
        else:
            callback(u'没输入城市你让我查个头啊...')

    def callback(self, resp, callback):
        html_doc = resp.body
        soup = BeautifulSoup(html_doc)
        #美丽的汤获取的数组，找到城市的PM25
        city_air_data_array = soup.find_all(attrs = {'class':'span12 data'})

        #获取数据更新时间
        city_aqi_update_array = \
                str(soup.find_all(attrs = {'class':'live_data_time'})[0])\
                .replace('<div class="live_data_time">\n','')

        city_aqi_update_time = city_aqi_update_array.replace('</div>', '').strip()
        city_aqi_update_time = city_aqi_update_time.replace('<p>', '')
        city_aqi_update_time = city_aqi_update_time.replace('</p>', '')


        #获取城市名
        target_city = "h2"
        city_name_str = str(soup.find_all(target_city)[0])\
                .replace('<%s>' % target_city,'')
        city_name = city_name_str.replace('</%s>' % target_city,'').strip()

        #获取城市空气质量
        target_city_aqi = "h4"
        city_aqi_str = str(soup.find_all(target_city_aqi)[0])\
                .replace('<%s>' % target_city_aqi,'')
        city_aqi = city_aqi_str.replace('</%s>' % target_city_aqi,'').strip()


        #获取城市各项指标的数据值，切割
        city_data_array = str(city_air_data_array[0]).strip()\
                .split('<div class="span1">\n')
        city_data_array.remove('<div class="span12 data">\n')
        city_data_array = [x.replace('<div class="value">\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('<div class="caption">\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('</div>\n</div>','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('</div>\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.lstrip().rstrip()
                           for x in city_data_array]
        city_data_array.pop()

        city_air_status_str=u"当前查询城市为：{0}，空气质量为：{1}\n{2}\n"\
                u"{3}\n点击链接查看完整空气质量报告:{4}{5}"\
                .format (city_name.decode("utf-8"), city_aqi.decode("utf-8"),
                         "\n".join(city_data_array).decode("utf-8"),
                         city_aqi_update_time.decode("utf-8"), PM25_URL,
                         self.city)

        callback(city_air_status_str)

    def convert2pinyin(self, words):
        """
        将中文转换为拼音
        """
        if words:
            pinyin = PinYin()
            pinyin.load_word()
            pinyin_array=pinyin.hanzi2pinyin(string=words)
            return "".join(pinyin_array)
        else:
            return ''

#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   recall
#   E-mail  :   tk86935367@vip.qq.com
#   Date    :   14/06/25 15:59:20
#   Desc    :   天气
#   
""" 替换原有的weather.py，并删除weather.pyc
"""

import json
import urllib,requests
import sys
from plugins import BasePlugin


# 使用百度API获取天气预报
class BaiduWeather():
    """docstring for BaiduWeather"""
    def __init__(self):
        self.url = "http://api.map.baidu.com/telematics/v3/weather?output=json&ak=8a47b6b4cfee5e398e63df510980697e&location="

    def search(self,city,callback):
	url = self.url +  city.encode('utf-8')                  #urllib.quote(city.decode(sys.stdin.encoding).encode('utf-8','replace'))
	res = requests.get(url)
	html = res.text
	json_data = json.loads(html)
	error = json_data.get('error')
	if error != 0:
	    body = u'不支持该城市'
	else:
	    result = json_data.get('results',u'没有结果')
	    weather = result[0]
	    c_city = weather.get('currentCity',None)
	    weather_data = weather.get('weather_data',None)
	    #print weather_data[0]
	    body = u'{0}\n今天：{1},{2},{3}\n明天：{4},{5},{6}'.format(c_city,weather_data[0].get('temperature'),weather_data[0].get('weather'),weather_data[0].get('wind'), \
	                                                weather_data[1].get('temperature'),weather_data[1].get('weather'),weather_data[1].get('wind'))
	callback(body)



class WeatherPlugin(BasePlugin):
    bdweather = None
    def is_match(self, from_uin, content, type):
        if content.startswith("-w"):
            self.city = content.split(" ")[1]
            self._format = u"\n {0}" if type == "g" else u"{0}"
	    if self.bdweather is None:
		self.bdweather = BaiduWeather()
            return True
        return False


    def handle_message(self, callback):
        self.bdweather.search(self.city, callback)


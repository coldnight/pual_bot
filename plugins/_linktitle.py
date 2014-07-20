#-*- coding: utf8 -*-
__desc__ = 'Fetch link title or info'

from functools import partial
import logging
import json
import time

from _fetchtitle import (
  TitleFetcher, MediaType,
  GithubFinder, GithubUserFinder,
  URLFinder,
  HtmlTitleParser,
)

from pyxmpp2.expdict import ExpiringDictionary
import tornado.ioloop
from tornado.httpclient import AsyncHTTPClient

httpclient = AsyncHTTPClient()

try:
  import regex as re
  # modified from http://daringfireball.net/2010/07/improved_regex_for_matching_urls
  # This may take too long for builtin regex to match e.g.
  # https://wiki.archlinux.org/index.php/USB_Installation_Media_(%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87)
  # This won't match http://[::1]
  link_re = re.compile(r'''\b(?:https?://|www\.|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|\([^\s()<>]+\))*\))+(?:\((?:[^\s()<>]+|\([^\s()<>]+\))*\)|[^\s`!()\[\]{};:'".,<>?？«»“”‘’）】。，])''', re.ASCII | re.I)
except ImportError:
  import re
  logging.warn('mrab regex module not available, using simpler URL regex.')
  link_re = re.compile(r'\b(?:https?://|www\.)[-A-Z0-9+&@#/%=~_|$?!:,.]*[A-Z0-9+&@#/%=~_|$]')

_cache = ExpiringDictionary(default_timeout=300)

_black_list = (
  r'p\.vim-cn\.com/\w{3}/?',
  r'^http://p\.gocmd\.net/\w{3}/?',
  r'^http://paste\.edisonnotes\.com/\w{3}/?',
  r'paste\.ubuntu\.(?:org\.cn|com)/\d+/?$',
  r'^http://paste\.pound-python\.org/show/',
  r'^http://bpaste\.net/show/',
  r'(?:susepaste|paste\.kde)\.org/\d+/?$',
  r'^https?://(?:gitcafe|geakit)\.com/',
  r'^http://ideone\.com/\w+$',
  r'^http://imgur\.com/\w+$',
  r'^https?://github\.com/\w+/\w+/(?!issues/|commit/).+',
  r'\$',
  r'code\.bulix\.org',
  r'slexy.org/view/\w+$',
  r'paste\.opensuse\.org/\d+$',
  r'^http://paste\.linuxzen\.com/show/\d+$',
  r'^http://paste\.fedoraproject\.org/',
  r'^http://pastebin\.centos\.org/\d+/?$',
  r'^http://fpaste.org/\w+/',
  r'^http://supercat-lab\.org/pastebox/.+',
  r'^https://groups\.google\.com/forum/#',
  r'^http://paste\.linuxzen\.com/p/',
  r'^http://0\.web\.qstatic\.com/webqqpic/style/face/',
  r'^http://www\.zhihu\.com/\?next=',
)

_black_list = tuple(re.compile(x) for x in _black_list)

_stop_url_pairs = (
  ('http://passport.weibo.com/visitor/visitor?', 'http://weibo.com/'),
  ('http://passport.weibo.com/visitor/visitor?', 'http://www.weibo.com/'),
  ('https://accounts.google.com/ServiceLogin?', 'https://www.google.com/'),
  ('https://accounts.google.com/ServiceLogin?', 'https://plus.google.com/'),
  ('https://accounts.google.com/ServiceLogin?', 'https://accounts.google.com/'),
  ('https://bitbucket.org/account/signin/', 'https://bitbucket.org/'),
  ('http://www.renren.com/SysHome.do?origURL=', 'http://www.renren.com/'),
)

def filesize(size):
  if size < 1024:
      num, unit = size, "B"

  elif size > 1024 and size < 1024 ** 2 :
      num, unit = size / 1024, "KB"
  elif size > 1024 ** 2 and size < 1024 ** 3:
      num, unit = size / (1024 ** 2), "MB"
  elif size > 1024 ** 3 and size < 1024 ** 4:
      num, unit = size / (1024 ** 3), "G"
  else:
      num, unit = size / (1024 ** 4), "T"

  return u"{0} {1}".format(num, unit)


def blacklisted(u):
  for i in _black_list:
    if i.search(u):
      return True
  return False

class StopURLs(URLFinder):
  @classmethod
  def _match_url(cls, url, fetcher):
    for login, origin in _stop_url_pairs:
      if url.startswith(login):
        last_url = fetcher.url_visited[-1]
        if last_url.startswith(origin):
          return True

  def __call__(self):
    self.done(False)

class SogouImage(URLFinder):
  _url_pat = re.compile(r'http://pinyin\.cn/.+$')
  _img_pat = re.compile(br'"http://input\.shouji\.sogou\.com/multimedia/[^.]+\.jpg"')
  def __call__(self):
    httpclient.fetch(self.fullurl, self._got_page)

  def _got_page(self, res):
    m = self._img_pat.search(res.body)
    if m:
      url = self.url = m.group()[1:-1].decode('latin1')
      call_fetcher(url, self._got_image, referrer=self.fullurl)

  def _got_image(self, info, fetcher):
    self.done(info)

class Imagebin(URLFinder):
  _url_pat = re.compile(r'http://imagebin\.org/(\d+)')
  _image_url = 'http://imagebin.org/index.php?mode=image&id='

  def __call__(self):
    url = self._image_url + self.match.group(1)
    call_fetcher(url, self._got_info, referrer=self.fullurl)

  def _got_info(self, info, fetcher):
    self.done(info)

class WeixinCopy(URLFinder):
  _url_pat = re.compile(r'http://mp\.weixin\.qq\.com/s\?')
  _src_pat = re.compile(br"var\s+msg_source_url\s+=\s+'([^']+)'")
  def __call__(self):
    httpclient.fetch(self.fullurl, self._got_page)

  def _got_page(self, res):
    m = self._src_pat.findall(res.body)
    if m:
      src = m[-1].decode('latin1')
      if src.endswith('#rd'):
        src = src[:-3]
    else:
      src = '(未知)'
    p = HtmlTitleParser()
    p.feed(res.body)
    if p.result:
      title = p.result
    else:
      title = '(未知)'
    self.done((title, src))

def format_github_repo(repoinfo):
  if not repoinfo['description']:
    repoinfo['description'] = '该仓库没有描述 :-('
  ans = '⇪Github 项目描述：%(description)s (%(language)s) ♡ %(watchers)d ⑂ %(forks)d，最后更新：%(updated_at)s' % repoinfo
  if repoinfo['fork']:
    ans += ' (forked)'
  ans += '。'
  return ans

def prepare_field(d, key, prefix):
  d[key] = prefix + d[key] if d.get(key, False) else ''

def format_github_user(userinfo):
  prepare_field(userinfo, 'blog', '，博客：')
  prepare_field(userinfo, 'company', '，公司：')
  prepare_field(userinfo, 'location', '，地址：')
  if 'name' not in userinfo:
    userinfo['name'] = userinfo['login']
  ans = '⇪Github %(type)s：%(name)s，%(public_repos)d 公开仓库，%(followers)d 关注者，关注 %(following)d 人%(blog)s %(company)s%(location)s，最后活跃时间：%(updated_at)s。' % userinfo
  return ans

def format_mediatype(info):
    ret = '⇪文件类型: ' + info.type
    if info.size:
      ret += ', 文件大小: ' + filesize(info.size)
    if info.dimension:
      s = info.dimension
      if isinstance(s, tuple):
        s = '%dx%d' % s
      ret += ', 图像尺寸: ' + s
    return ret

def replylinktitle(reply, info, fetcher):
  timeout = None
  finderC = fetcher.finder.__class__
  if info is False:
    _cache.set_item(fetcher.origurl, False, 86400)
    logging.info('url skipped: %s', fetcher.origurl)
    return
  elif finderC is Imagebin:
    ans = '⇪Imagebin 图片: %s' % format_mediatype(info)[3:]
  elif finderC is WeixinCopy:
    ans = '⇪微信转载文章标题: %s，来源: %s' % info
  elif finderC is SogouImage:
    print(info)
    ans = '⇪搜索输入法图片: %s' % format_mediatype(info)[3:]
  elif isinstance(info, str):
    # take at most 100 characters
    if len(info) > 100:
      info = info[:100].rstrip() + '...'
    info = info.strip()
    if fetcher.status_code != 200:
      info = '[%d] ' % fetcher.status_code + info
    ans = '⇪网页标题: ' + info.replace('\n', '')
  elif isinstance(info, MediaType):
    ans = format_mediatype(info)
  elif info is None:
    ans = '该网页没有标题 :-('
  elif isinstance(info, dict): # github json result
    res = fetcher.finder.response
    if res.code != 200:
      logging.warn('Github{,User}Finder returned HTTP code %s (body is %s).', res.code, res.body)
      ans = '[Error %d]' % res.code
    else:
      if finderC is GithubFinder:
        ans = format_github_repo(info)
      elif finderC is GithubUserFinder:
        ans = format_github_user(info)
      else:
        logging.error('got a dict of unknown type: %s', finderC.__name__)
        ans = '（内部错误）'
  else:
    ans = '出错了！' + repr(info)
    timeout = 10

  if fetcher.origurl != fetcher.fullurl:
    ans += ' (重定向到 %s )' % fetcher.fullurl

  logging.info('url info: %s', ans)
  reply(fetcher.origurl, ans, timeout=timeout)

def call_fetcher(url, callback, referrer=None):
  fetcher = TitleFetcher(url, callback, referrer=referrer, url_finders=(
    GithubFinder, GithubUserFinder,
    Imagebin, WeixinCopy, SogouImage, StopURLs,
  ), run_at_init=False)
  try:
    fetcher.run()
  except UnicodeError as e:
    callback(e, fetcher)

def getTitle(u, reply, how=replylinktitle):
  try:
    # ExpiringDictionary.get won't do expiration
    cached = _cache[u]
    logging.info('fetched url info: %r (%s)', cached, u)
    if cached:
      reply(cached)
  except KeyError:
    logging.info('fetching url: %s', u)
    call_fetcher(u, partial(how, partial(_cache_and_reply, reply)))

def _cache_and_reply(reply, key, msg, timeout=None):
  _cache.set_item(key, msg, timeout)
  reply(msg)

def fetchtitle(urls, reply):
  for u in urls:
    getTitle(u, reply)

# vim:se sw=2:

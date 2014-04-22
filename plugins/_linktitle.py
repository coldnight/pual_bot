#!/usr/bin/env python
#-*- coding: utf-8 -*-
__desc__ = 'Fetch link title or info'

from functools import partial
import logging

from _fetchtitle import (
  TitleFetcher, MediaType,
  GithubFinder, GithubUserFinder,
  URLFinder,
)

from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop

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


_black_list = (
  r'p\.vim-cn\.com/\w{3}/?',
  r'^http://p\.gocmd\.net/\w{3}/?',
  r'^http://paste\.edisonnotes\.com/\w{3}/?',
  r'paste\.ubuntu\.(?:org\.cn|com)/\d+/?$',
  r'(?:imagebin|susepaste|paste\.kde)\.org/\d+/?$',
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
  r'^http://127\.0\.0\.1',
  r'^http://localhost',
  r'^https://localhost',
  r'^localhost',
)

_black_list = tuple(re.compile(x) for x in _black_list)

_stop_url_pairs = (
  ('http://weibo.com/signup/', 'http://weibo.com/'),
  ('http://weibo.com/signup/', 'http://www.weibo.com/'),
  ('http://weibo.com/login.php?url=', 'http://weibo.com/'),
  ('http://weibo.com/login.php?url=', 'http://www.weibo.com/'),
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

def format_github_repo(repoinfo):
  if not repoinfo['description']:
    repoinfo['description'] = u'该仓库没有描述 :-('
  ans = u'⇪Github 项目描述：%(description)s (%(language)s) ♡ %(watchers)d ⑂ %(forks)d，最后更新：%(updated_at)s' % repoinfo
  if repoinfo['fork']:
    ans += ' (forked)'
  ans += u'。'
  return ans

def prepare_field(d, key, prefix):
  d[key] = prefix + d[key] if d.get(key, False) else ''

def format_github_user(userinfo):
  prepare_field(userinfo, u'blog', u'，博客：')
  prepare_field(userinfo, u'company', u'，公司：')
  prepare_field(userinfo, u'location', u'，地址：')
  if 'name' not in userinfo:
    userinfo['name'] = userinfo['login']
  ans = u'⇪Github %(type)s：%(name)s，%(public_repos)d 公开仓库，%(followers)d 关注者，关注 %(following)d 人%(blog)s %(company)s%(location)s，最后活跃时间：%(updated_at)s。' % userinfo
  return ans

def format_mediatype(info):
    ret = u'⇪文件类型: ' + info.type
    if info.size:
      ret += u', 文件大小: ' + filesize(info.size)
    if info.dimension:
      s = info.dimension
      if isinstance(s, tuple):
        s = u'%dx%d' % s
      ret += u', 图像尺寸: ' + s
    return ret

def replylinktitle(reply, info, fetcher):
  if isinstance(info, bytes):
    try:
      info = info.decode('gb18030')
    except UnicodeDecodeError:
      pass

  timeout = None
  finderC = fetcher.finder.__class__
  if info is False:
    logging.info('url skipped: %s', fetcher.origurl)
    return
  elif finderC is SogouImage:
    print(info)
    ans = u'⇪搜索输入法图片: %s' % format_mediatype(info)[3:]
  elif isinstance(info, basestring):
    if fetcher.status_code != 200:
      info = '[%d] ' % fetcher.status_code + info
    ans = u'⇪网页标题: ' + info.replace('\n', '')
  elif isinstance(info, MediaType):
    ans = format_mediatype(info)
  elif info is None:
    ans = u'该网页没有标题 :-('
  elif isinstance(info, dict): # github json result
    res = fetcher.finder.response
    if res.code != 200:
      logging.warn(u'Github{,User}Finder returned HTTP code %s (body is %s).', res.code, res.body)
      ans = u'[Error %d]' % res.code
    else:
      if finderC is GithubFinder:
        ans = format_github_repo(info)
      elif finderC is GithubUserFinder:
        ans = format_github_user(info)
      else:
        logging.error(u'got a dict of unknown type: %s', finderC.__name__)
        ans = u'（内部错误）'
  else:
    ans = u'出错了！ {0}'.format(info)

  if fetcher.origurl != fetcher.fullurl:
    ans += u' (重定向到 %s )' % fetcher.fullurl

  logging.info(u'url info: %s', ans)
  reply(ans)

def call_fetcher(url, callback, referrer=None):
  fetcher = TitleFetcher(url, callback, referrer=referrer, url_finders=(
    GithubFinder, GithubUserFinder, SogouImage, StopURLs), run_at_init=False)
  try:
    fetcher.run()
  except UnicodeError as e:
    callback(e, fetcher)

def getTitle(u, reply):
  logging.info('fetching url: %s', u)
  call_fetcher(u, partial(replylinktitle, reply))


def get_urls(msg):
  seen = set()
  for m in link_re.finditer(msg):
    u = m.group(0)
    if u not in seen:
      if blacklisted(u):
        continue
      if not u.startswith("http"):
        if msg[m.start() - 3: m.start()] == '://':
          continue
        u = 'http://' + u
        if u in seen:
          continue
        if u.count('/') == 2:
          u += '/'
        if u in seen:
          continue
      seen.add(u)
  return seen

def fetchtitle(urls, reply):
  for u in urls:
    getTitle(u, reply)

def register(bot):
  bot.register_msg_handler(fetchtitle)


if __name__ == "__main__":
  def cb(tt):
    print tt
  fetchtitle(["http://www.baidu.com"], cb)
  IOLoop.instance().start()
# vim:se sw=2:

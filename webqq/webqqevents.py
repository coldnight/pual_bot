#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   wh
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 10:56:31
#   Desc    :   WebQQ 事件
#

from mainloop.interfaces import  Event

class WebQQEvent(Event):
    webqq = None
    handler = None

class CheckedEvent(WebQQEvent):
    def __init__(self, check_data, handler):
        self.check_data = check_data
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Checked: {0}".format(self.check_data)


class BeforeLoginEvent(WebQQEvent):
    def __init__(self, back_data, handler):
        self.back_data = back_data
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Before Login: {0}".format(self.back_data)


class WebQQLoginedEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Logined"


class WebQQHeartbeatEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Heartbeat"


class WebQQPollEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return "WebQQ Poll"


class WebQQMessageEvent(WebQQEvent):
    def __init__(self, msg, handler):
        self.handler = handler
        self.message = msg

    def __unicode__(self):
        return u"WebQQ Got msg: {0}".format(self.message)

class RetryEvent(WebQQEvent):
    def __init__(self, cls, req, handler, err = None, *args, **kwargs):
        self.cls = cls
        self.req = req
        self.handler = handler
        self.args = args
        self.kwargs = kwargs
        self.err = err

    def __unicode__(self):
        return u"{0} Retry with Error {1}".format(self.cls.__name__, self.err)

class RemoveEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"Remove Handler {0}".format(self.handler.__class__.__name__)



class GroupListEvent(WebQQEvent):
    def __init__(self, handler, data):
        self.handler = handler
        self.data = data

    def __unicode__(self):
        return u"WebQQ Update Group List"

class WebQQRosterUpdatedEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Roster Updated"


class GroupMembersEvent(WebQQEvent):
    def __init__(self, handler, data, gcode):
        self.handler = handler
        self.data = data
        self.gcode = gcode

    def __unicode__(self):
       return u"WebQQ fetch group members"


class ReconnectEvent(WebQQEvent):
    def __init__(self, handler):
        self.handler = handler

    def __unicode__(self):
        return u"WebQQ Reconnect.."


class FriendsUpdatedEvent(WebQQEvent):
    def __init__(self, handler, data):
        self.handler = handler
        self.data = data

    def __unicode__(self):
        return u"Friends list updated"

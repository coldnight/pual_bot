#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   Wood.D Wong
#   E-mail  :   wh_linux@126.com
#   Date    :   13/03/08 10:54:27
#   Desc    :   Epoll main Loop
#

from __future__ import absolute_import, division
import select
from .interfaces import HandlerReady, PrepareAgain
from .base import MainLoopBase

from ..utils import get_logger

class EpollMainLoop(MainLoopBase):
    """ Main event loop based on the epoll() syscall on Linux system """
    def __init__(self, settings = None, handlers= None):
        self.READ_ONLY = (select.EPOLLIN | select.EPOLLPRI | select.EPOLLHUP |
                    select.EPOLLERR |select.EPOLLET)
        self.READ_WRITE = self.READ_ONLY | select.EPOLLOUT
        self.WRITE_ONLY = select.EPOLLOUT
        self.epoll = select.epoll()
        self._handlers = {}
        self._unprepared_handlers = {}
        self._timeout = None
        self._exists_fd = {}
        self.logger = get_logger()
        MainLoopBase.__init__(self, settings, handlers)

        return

    def _add_io_handler(self, handler):
        self._unprepared_handlers[handler] = None
        self._configure_io_handler(handler)

    def _configure_io_handler(self, handler):
        if self.check_events():
            return
        if handler in self._unprepared_handlers:
            old_fileno = self._unprepared_handlers[handler]
            prepared = self._prepare_io_handler(handler)
        else:
            old_fileno = None
            prepared = True
        fileno = handler.fileno()
        if old_fileno is not None and fileno != old_fileno:
            del self._handlers[old_fileno]
            self._exists_fd.pop(old_fileno, None)
            self.epoll.unregister(old_fileno)
        if not prepared:
            self._unprepared_handlers[handler] = fileno

        if not fileno:
            return

        self._handlers[fileno] = handler
        events = 0
        if handler.is_readable():
            self.logger.debug(" {0!r} readable".format(handler))
            events |= self.READ_ONLY
        if handler.is_writable():
            self.logger.debug(" {0!r} writable".format(handler))
            events |= self.READ_WRITE

        if events is not None: # events may be 0
            if fileno in self._exists_fd and events != 0:
                self.epoll.modify(fileno, events)
            elif fileno in self._exists_fd and events == 0:
                self._remove_io_handler(handler)
            else:
                self._exists_fd.update({fileno:1})
                self.epoll.register(fileno, events)

    def _prepare_io_handler(self, handler):
        ret = handler.prepare()
        if isinstance(ret, HandlerReady):
            del self._unprepared_handlers[handler]
            prepared = True
        elif isinstance(ret, PrepareAgain):
            if ret.timeout is not None:
                if self._timeout is not None:
                    self._timeout = min(self._timeout, ret.timeout)
                else:
                    self._timeout = ret.timeout
            prepared = False
        else:
            raise TypeError("Unexpected result from prepare()")

        return prepared

    def _remove_io_handler(self, handler):
        if handler in self._unprepared_handlers:
            old_fileno = self._unprepared_handlers[handler]
            del self._unprepared_handlers[handler]
        else:
            old_fileno = handler.fileno()
        if old_fileno is not None:
            try:
                del self._handlers[old_fileno]
                self._exists_fd.pop(old_fileno, None)
                self.epoll.unregister(old_fileno)
            except KeyError:
                pass

    def loop_iteration(self, timeout = 60):
        next_timeout, sources_handled = self._call_timeout_handlers()
        if self.check_events():
            return
        if self._quit:
            return sources_handled
        for handler in list(self._unprepared_handlers):
            self._configure_io_handler(handler)
        if self._timeout is not None:
            timeout = min(timeout, self._timeout)
        if next_timeout is not None:
            timeout = min(next_timeout, timeout)

        if timeout == 0:
            timeout += 1    # 带有超时的非阻塞,解约资源
        events = self.epoll.poll(timeout)
        for fd, flag in events:
            if flag & (select.EPOLLIN | select.EPOLLPRI | select.EPOLLET):
                self._handlers[fd].handle_read()
            if flag & (select.EPOLLOUT|select.EPOLLET):
                self._handlers[fd].handle_write()
            if flag & (select.EPOLLERR | select.EPOLLET):
                self._handlers[fd].handle_err()
            if flag & (select.EPOLLHUP | select.EPOLLET):
                self._handlers[fd].handle_hup()
            #if flag & select.EPOLLNVAL:
                #self._handlers[fd].handle_nval()

            sources_handled += 1
            self._configure_io_handler(self._handlers[fd])

        return sources_handled



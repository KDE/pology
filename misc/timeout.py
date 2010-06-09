# -*- coding: UTF-8 -*-

"""
A timeout decorator.

Based on SIGALRM from an activeState Python recipe by Chris Wright,
U{http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/307871}.

@author: Sébastien Renard <sebastien.renard@digitalfox.org>
@license: GPLv3
"""

import signal

from pology import PologyError, _, n_
from pology.misc.report import report


class TimedOutException (PologyError):

    def __init__ (self, value="timed-out"):

        self.value = value

        PologyError.__init__(str(self))

    def __str__ (self):

        return repr(self.value)


def timed_out (timeout):

    def decorate (f):

        def handler (signum, frame):
            report(_("@info:progress",
                     ">>>>> Timed out! <<<<<"))
            raise TimedOutException()

        def new_f (*args, **kwargs):
            old = signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)
            try:
                result = f(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
            return result

        new_f.func_name = f.func_name
        return new_f

    return decorate


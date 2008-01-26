# -*- coding: UTF-8 -*-

"""A timeout decorator based on SIGALRM from an activeState Python recipe by Chris Wright
http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/307871"""


import signal

class TimedOutException(Exception):
    def __init__(self, value = "Timed Out"):
        Exception.__init__(self)
        self.value = value
    def __str__(self):
        return repr(self.value)

def timed_out(timeout):
    def decorate(f):
        def handler(signum, frame):
            print ">>>> Got timeout ! <<<<<"
            raise TimedOutException()
        
        def new_f(*args, **kwargs):
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

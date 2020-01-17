# -*- coding: UTF-8 -*-

"""
Collections of multiple sequences.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

class Multidict (object):
    """
    Several dictionaries readable as one.

    Allows to get elements from several dictionary-like sequences
    as if they were one, without really creating a single union
    of items from all of them.
    This is useful when it is more expensive to create the union,
    than to look sequentially in each dictionary in turn.

    All methods named same as in C{dict} have same semantics too.
    """

    def __init__ (self, dicts):
        """
        Constructor.

        Order of dictionaries in the list matters,
        firstmost has highest priority when looking for a key.

        Collected sequences need to implement the following methods of
        a dictionary: C{__getitem__}, C{__contains__},
        C{iterkeys}, C{itervalues}, C{iteritems}.
        Iterators have to implement C{next} method,
        and raise C{StopIteration} when exhausted.

        @param dicts: sequence of dictionary-like objects
        @type dicts: list of dict
        """

        self._dicts = dicts


    def __contains__ (self, key):

        for d in self._dicts:
            if key in d:
                return True

        return False


    def __getitem__ (self, key):

        for d in self._dicts:
            if key in d:
                return d[key]

        raise KeyError(key)


    def __iter__ (self):

        return iter(self.keys())


    def get (self, key, defval=None):

        for d in self._dicts:
            if key in d:
                return d[key]

        return defval


    def iterkeys (self):

        return self._Iterator(lambda x: iter(x.keys()))


    def itervalues (self):

        return self._Iterator(lambda x: iter(x.values()))


    def iteritems (self):

        return self._Iterator(lambda x: iter(x.items()))


    class _Iterator (object):

        def __init__ (self, getit):
            self._iters = [getit(d) for d in self._dicts]

        def __iter__ (self):
            return self

        def __next__ (self):
            while self._iters:
                try:
                    return next(self._iters[0])
                except StopIteration:
                    self._iters.pop(0)
            raise StopIteration


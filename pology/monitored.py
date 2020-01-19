# -*- coding: UTF-8 -*-

"""
Framework for monitored classes.

Includes the base class that monitored classes should inherit from,
and some monitored partial counterparts to standard Python data types.
Monitored objects are limited to prescribed set of public instance variables,
and, optionally, the values which can be assigned to those are limited to
a prescribed set of types. Each public instance variable has a I{shadowing}
modification counter, an instance variable which counts the changes made to
the variable which it shadows.

As of yet, this module and its functionality is for internal use in
core PO interface classes (L{Catalog}, L{Message}...), not intended
for creation of monitored classes in client code.
Use this documentation only to find out which of the methods available
in standard data types are available through their monitored counterparts
(e.g. L{Monlist} compared to C{list}).

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

from pology import PologyError, _, n_

# =============================================================================
# Internal functions.

def _gather_modcount (obj):
    modcount = 0
    for cnt in getattr(obj, "#", {}).values(): # own counts
        modcount += cnt
    for att in getattr(obj, "_spec", {}): # sub counts
        if att != "*": # single sub counts
            if not obj._spec[att].get("derived", False):
                modcount += getattr(obj.__dict__["_" + att], "modcount", 0)
        else:
            for itemobj in obj.__dict__[att]: # sequence sub counts
                modcount += getattr(itemobj, "modcount", 0)
    return modcount

def _scatter_modcount (obj, val):
    if hasattr(obj, "#"):
        for att in obj.__dict__["#"]:
            obj.__dict__["#"][att] = val
    for att in getattr(obj, "_spec", {}):
        if att != "*":
            if not obj._spec[att].get("derived", False):
                subobj = obj.__dict__["_" + att]
                if hasattr(subobj, "modcount"):
                    subobj.modcount = val
        else:
            for itemobj in obj.__dict__[att]:
                if hasattr(itemobj, "modcount"):
                    itemobj.modcount = val

def _assert_spec_single (att, obj, spec):
    if "type" in spec:
        if not isinstance(obj, spec["type"]):
            if att != "*":
                raise PologyError(
                    _("@info",
                      "Expected %(type1)s for attribute '%(attr)s', "
                      "got %(type2)s.",
                      type1=spec["type"], attr=att, type2=type(obj)))
            else:
                raise PologyError(
                    _("@info",
                      "Expected %(type1)s for sequence element, "
                      "got %(type2)s.",
                      type1=spec["type"], type2=type(obj)))
    if "spec" in spec:
        _assert_spec_init(obj, spec["spec"])

def _assert_spec_init (self, spec):
    for att, subspec in spec.items():
        if att != "*":
            if not subspec.get("derived", False):
                _assert_spec_single(att, self.__dict__["_" + att], subspec)
        else:
            for itemobj in self.__dict__[att]:
                _assert_spec_single(att, itemobj, subspec)
    # All checks done, add spec and counts.
    self._spec = spec
    self.__dict__["#"] = {}
    for att in spec:
        if not spec[att].get("derived", False):
            self.__dict__["#"][att] = 0

# =============================================================================
# Base class for monitored classes.

class Monitored (object):
    """
    Base class for monitored classes.

    Internal.
    """

    def __getattr__ (self, att):
        attp = "_" + att
        if att.startswith("_"):
            return self.__dict__[att]
        elif att == "modcount":
            return _gather_modcount(self)
        elif att.endswith("_modcount"):
            return self.__dict__["#"][att[:-len("_modcount")]]
        elif att == "#":
            return self.__dict__[att]
        else:
            return self.__dict__[attp]

    def __setattr__ (self, att, val):
        if att.startswith("_"):
            self.__dict__[att] = val
        else:
            if att == "modcount" or att.endswith("_modcount"):
                # Only set if given to 0, ignore silently other values.
                if isinstance(val, int) and val == 0:
                    if att == "modcount":
                        _scatter_modcount(self, val)
                    else:
                        attb = att[:-len("_modcount")]
                        attbp = "_" + attb
                        self.__dict__["#"][attb] = val
                        _scatter_modcount(self.__dict__[attbp], val)
            else:
                self.assert_spec_setattr(att, val)
                attp = "_" + att
                cval = self.__dict__[attp]
                if cval != val:
                    self.__dict__["#"][att] += 1
                if hasattr(cval, "modcount"):
                    mc_diff = cval.modcount - val.modcount
                    if mc_diff > 0:
                        self.__dict__["#"][att] += mc_diff
                self.__dict__[attp] = val

    def __eq__ (self, other):
        return isinstance(self, type(other)) and self.data() == other.data()

    def __ne__ (self, other):
        return not isinstance(self, type(other)) or self.data() != other.data()

    def data (self):
        if hasattr(self, "_spec"):
            d = {}
            for att in self._spec:
                if att != "*":
                    subobj = self.__getattr__(att)
                else:
                    subobj = self.__dict__[att]
                if hasattr(subobj, "data"):
                    d[att] = subobj.data()
                else:
                    d[att] = subobj
            d["#"] = self.__dict__["#"]
            return d

    def assert_spec_init (self, spec):
        _assert_spec_init(self, spec)

    def assert_spec_setattr (self, att, subobj):
        if not hasattr(self, "_spec"):
            return
        if att in self._spec:
            spec = self._spec[att]
            if spec.get("derived", False):
                raise PologyError(
                    _("@info",
                      "Derived attribute '%(attr)s' is read-only.",
                      attr=att))
            _assert_spec_single(att, subobj, spec)
        elif att.endswith("_modcount"):
            if not isinstance(subobj, int):
                raise PologyError(
                    _("@info",
                      "Expected %(type1)s for attribute '%(attr)s', "
                      "got %(type2)s.",
                      type1=int, attr=att, type2=type(subobj)))
        else:
            raise PologyError(
                _("@info",
                  "Attribute '%(attr)s' is not among specified.",
                  attr=att))

    def assert_spec_getattr (self, att):
        if not hasattr(self, "_spec"):
            return
        if att not in self._spec:
            raise PologyError(
                _("@info",
                  "Attribute '%(attr)s' is not among specified.",
                  attr=att))

    def assert_spec_setitem (self, itemobj):
        if not hasattr(self, "_spec"):
            return
        if "*" in self._spec:
            _assert_spec_single("*", itemobj, self._spec["*"])
        else:
            raise PologyError(
                _("@info",
                  "Object '%(obj)s' is not specified to be a sequence.",
                  obj=self))

    def assert_spec_getitem (self):
        if not hasattr(self, "_spec"):
            return
        if "*" not in self._spec:
            raise PologyError(
                _("@info",
                  "Object '%(obj)s' is not specified to be a sequence.",
                  obj=self))

# =============================================================================
# Monitored pair.

_Monpair_spec = {
    "first" : {},
    "second" : {},
}

class Monpair (Monitored):
    """
    Monitored pair (counterpart to two-element C{tuple}).

    @ivar first: the first element of the pair
    @ivar second: the second element of the pair
    """

    def __init__ (self, init=None):
        """
        Create a pair with two elements.

        All methods behave as their namesakes in standard C{tuple}.

        @param init: 2-element sequence or another pair
        @param init: tuple, list,... or Monpair
        """

        if not isinstance(init, Monpair):
            pair = tuple(init)
            if len(pair) != 2:
                raise PologyError(
                    _("@info",
                      "Initializer sequence for a pair must contain "
                      "exactly two elements."))
            self._first, self._second = pair
        else:
            self._first = init.first
            self._second = init.second
        self.assert_spec_init(_Monpair_spec)


    def __repr__ (self):

        elfmt = ", ".join((repr(self._first), repr(self._second)))
        return "%s([%s])" % (self.__class__.__name__, elfmt)


    def __str__ (self):

        return self.__repr__()


    def __len__ (self):

        return 2


    def __iter__ (self):

        return iter((self._first, self._second))


    def __getitem__ (self, i):

        if i == 0:
            return self._first
        elif i == 1:
            return self._second
        else:
            raise IndexError


# =============================================================================
# Monitored list.

_Monlist_spec = {
    "*" : {},
}

class Monlist (Monitored):
    """
    Monitored list.
    """

    def __init__ (self, lst=None):
        """
        Create a monitored list from a sequence.

        All methods behave as their namesakes in standard C{list}.

        @param lst: sequence of elements
        @type lst: any convertible into list by C{list()}
        """

        if lst is not None:
            self.__dict__["*"] = list(lst)
        else:
            self.__dict__["*"] = list()
        self.assert_spec_init(_Monlist_spec)


    def __repr__ (self):

        elfmt = ", ".join(repr(x) for x in self.__dict__["*"])
        return "%s([%s])" % (self.__class__.__name__, elfmt)


    def __str__ (self):

        return self.__repr__()


    def __len__ (self):

        return len(self.__dict__["*"])


    def __getitem__ (self, i):

        self.assert_spec_getitem()
        if not isinstance(i, slice):
            return self.__dict__["*"][i]
        else:
            return Monlist(self.__dict__["*"][i])


    def __setitem__ (self, i, val):

        if not isinstance(i, slice):
            self.assert_spec_setitem(val)
        else:
            for v in val:
                self.assert_spec_setitem(v)
        cval = self.__dict__["*"][i]
        if cval != val:
            self.__dict__["#"]["*"] += 1
        if hasattr(cval, "modcount"):
            mc_diff = cval.modcount - val.modcount
            if mc_diff > 0:
                self.__dict__["#"]["*"] += mc_diff
        self.__dict__["*"][i] = val


    def __delitem__ (self, i):

        self.assert_spec_getitem()
        nitems = len(self.__dict__["*"])
        del self.__dict__["*"][i]
        if len(self.__dict__["*"]) != nitems:
            self.__dict__["#"]["*"] += 1


    def __eq__ (self, other):

        if len(self.__dict__["*"]) != len(other):
            return False
        for i in range(len(other)):
            if self.__dict__["*"][i] != other[i]:
                return False
        return True


    def __ne__ (self, other):

        return not self.__eq__(other)


    def __add__ (self, other):

        lst = Monlist(self.__dict__["*"])
        lst.extend(other)
        return lst


    def append (self, val):

        self.assert_spec_setitem(val)
        self.__dict__["*"].append(val)
        self.__dict__["#"]["*"] += 1


    def extend (self, other):

        for val in other:
            self.append(val)


    def remove (self, val):

        self.assert_spec_setitem(val)
        if val in self.__dict__["*"]:
            self.__dict__["*"].remove(val)
            self.__dict__["#"]["*"] += 1


    def pop (self, i=None):

        if i is None:
            val = self.__dict__["*"].pop()
        else:
            val = self.__dict__["*"].pop(i)
        self.__dict__["#"]["*"] += 1
        return val


    def insert (self, i, val):

        self.assert_spec_setitem(val)
        self.__dict__["*"].insert(i, val)
        self.__dict__["#"]["*"] += 1


# =============================================================================
# Monitored set.

_Monset_spec = {
    "*" : {},
}

class Monset (Monitored):
    """
    Monitored set.
    """

    def __init__ (self, st=None):
        """
        Create a monitored set from a sequence.

        All methods behave as their namesakes in standard C{set}.

        @param st: sequence of elements
        @type st: any convertible into list by C{list()}
        """

        self.__dict__["*"] = list()
        if st is not None:
            for val in st:
                if val not in self.__dict__["*"]:
                    self.__dict__["*"].append(val)
        self.assert_spec_init(_Monset_spec)


    def __repr__ (self):

        elfmt = ", ".join(repr(x) for x in self.__dict__["*"])
        return "%s([%s])" % (self.__class__.__name__, elfmt)


    def __str__ (self):

        return self.__repr__()


    def __len__ (self):

        return len(self.__dict__["*"])


    def __iter__ (self):

        return iter(self.__dict__["*"])


    def __eq__ (self, other):

        if len(self.__dict__["*"]) != len(other):
            return False
        for i in range(len(other)):
            if self.__dict__["*"][i] not in other:
                return False
        return True


    def __ne__ (self, other):

        return not self.__eq__(other)


    def __contains__ (self, val):

        return val in self.__dict__["*"]


    def add (self, val):

        self.assert_spec_setitem(val)
        if val not in self.__dict__["*"]:
            self.__dict__["*"].append(val)
            self.__dict__["#"]["*"] += 1


    def remove (self, val):

        self.assert_spec_setitem(val)
        if val in self.__dict__["*"]:
            self.__dict__["*"].remove(val)
            self.__dict__["#"]["*"] += 1


    def items (self):

        return list(self.__dict__["*"])


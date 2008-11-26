# -*- coding: UTF-8 -*-

"""
Handle subcommands and their parameters.

Subcommands are putting main command into different modes of operation.
Main commands with subcommands are typical of package managers, version
control systems, etc. This module provides a handler to conveniently load
subcommands on demand, and parser to extract and route parameters to them
from the command line.

The command line interface consists of having subcommand a free parameter,
and a special collector-option to collect parameters for the subcommand::

    $ cmd -a -b -c \  # command and any usual options
          subcmd \    # subcommand
          -s foo \    # subcommand parameter 'foo', without value (flag)
          -s bar:xyz  # subcommand parameter 'bar', with the value 'xyz'

where C{-s} is the collector-option, repeated for as many subcommand
parameters as needed. The collector-option can be freely positioned in
the command line, before or after the subcommand name, and mixed with
other options.

The format of subcommand parameter is either C{param} for flag parameters, C{param:value} for parameters taking a value, or C{param:value1,value2,...}
for parameters taking a list of values. Instead of, or in addition to using comma-separated string to represent the list, some parameters can be repeated
on the command line, and all the values collected to make the list.

Several subcommands may be given too, in which case a each subcommand
parameter is routed to every subcommand which expects it. This means that
all those subcommands should place the same semantics into the same-named
parameter they are using.

@note: For any of the methods in this module, the order of keyword parameters
is not guaranteed. Always name them in calls.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

# NOTE: The original code for this module was taken from the Divergloss
# glossary processor, and reduced and retouched for the needs in Pology.
# Actually, the main reason for not using Divergloss' module directly
# is to avoid dependency.

import os
import re
from textwrap import TextWrapper
import fnmatch

from pology.misc.report import error

def _p_ (x, y):
    return y


class ParamParser (object):
    """
    Parser for subcommand parameters.
    """

    def __init__ (self):
        """
        Constructor.
        """

        self._scviews = {}


    def add_subcmd (self, subcmd, desc=None):
        """
        Add a subcommand for which the parameters may be added afterwards.

        Use double-newline in the description for splitting into paragraphs.
        The description can also be set later, using C{set_desc} method of
        subcommand view.

        @param subcmd: subcommand name
        @type subcmd: string
        @param desc: description of the subcommand
        @type desc: string or C{None}

        @return: subcommand view
        @rtype: L{SubcmdView}
        """

        if subcmd in self._scviews:
            error(_p_("error message",
                     "trying to add subcommand '%(cmd)s' once again")
                  % dict(cmd=subcmd))

        self._scviews[subcmd] = SubcmdView(self, subcmd, desc)

        return self._scviews[subcmd]


    def get_view (self, subcmd):
        """
        The view into previously defined subcommand.

        @param subcmd: subcommand name
        @type subcmd: string

        @return: subcommand view
        @rtype: L{SubcmdView}
        """

        scview = self._scviews.get(subcmd, None)
        if scview is None:
            error(_p_("error message",
                     "trying to get a view for an unknown "
                     "subcommand '%(cmd)s'") % dict(cmd=subcmd))
        return scview


    def help (self, subcmds=None, wcol=79):
        """
        Formatted help for subcommands.

        @param subcmds: subcommand names (all subcommands if C{None})
        @type subcmds: list of strings
        @param wcol: column to wrap text at (<= 0 for no wrapping)
        @type wcol: int

        @return: formatted help
        @rtype: string
        """

        if subcmds is None:
            subcmds = self._scviews.keys()
            subcmds.sort()

        fmts = []
        for subcmd in subcmds:
            scview = self._scviews.get(subcmd, None)
            if scview is None:
                error(_p_("error message",
                         "trying to get help for an unknown "
                         "subcommand '%(cmd)s'") % dict(cmd=subcmd))
            fmts.append(scview.help(wcol))
            fmts.append("")

        return "\n".join(fmts)


    def listcmd (self, subcmds=None, wcol=79):
        """
        Formatted listing of subcommands with short descriptions.

        @param subcmds: subcommand names (all subcommands if C{None})
        @type subcmds: list of strings
        @param wcol: column to wrap text at (<= 0 for no wrapping)
        @type wcol: int

        @return: formatted listing
        @rtype: string
        """

        if subcmds is None:
            subcmds = self._scviews.keys()
            subcmds.sort()

        maxsclen = max([len(x) for x in subcmds])

        ndsep = _p_("subcommand listing: splitter between subcommand name "
                   "and description",
                   " - ")

        initin = " " * 2
        subsin = initin + " " * 4
        wrapper = TextWrapper(initial_indent=initin,
                              subsequent_indent=subsin,
                              width=wcol)
        fmts = []
        for subcmd in subcmds:
            scview = self._scviews.get(subcmd, None)
            if scview is None:
                error(_p_("error message",
                         "trying to include an unknown subcommand '%(cmd)s' "
                         "in listing") % dict(cmd=subcmd))
            desc = scview.shdesc()
            if desc:
                name = ("%%-%ds" % maxsclen) % subcmd
                s = name + ndsep + desc
            else:
                s = name
            fmts.extend(wrapper.wrap(s))

        return "\n".join(fmts)


    def parse (self, rawpars, subcmds, abort=False):
        """
        Parse the list of parameters collected from the command line.

        If the command line had parameters specified as::

            -sfoo -sbar:xyz -sbaz:10

        then the function call should get the list::

            rawpars=['foo', 'bar:xyz', 'baz:10']

        Result of parsing will be a dictionary of objects by subcommand name,
        where each object has attributes named like subcommand parameters.
        If attribute name has not been explicitly defined for a parameter,
        its parameter name will be used; if not a valid identifier by itself,
        it will be normalized by replacing all troublesome characters with
        an underscore, collapsing contiguous underscore sequences to a single
        underscore, and prepending an 'x' if it does not start with a letter.

        If a parameter is parsed which is not accepted by any of the given
        subcommands, its name is added to list of non-accepted parameters,
        which is the second element of the return tuple.
        Alternatively, execution may be aborted, with non-accepted parameters
        reported to stderr.

        @param rawpars: raw parameters
        @type rawpars: list of strings
        @param subcmds: names of issued subcommands
        @type subcmds: list of strings
        @param abort: whether to abort execution when some parameters
            were not accepted by any subcommand
        @type abort: bool

        @return: objects with parameters as attributes, and
            list of parameter names not accepted by any of subcommands
        @rtype: dict of objects by subcommand name and list of strings
        """

        # Assure only registered subcommands have been issued.
        for subcmd in subcmds:
            if subcmd not in self._scviews:
                error(_p_("error in command line (subcommand)",
                         "unregistered subcommand '%(cmd)s' issued")
                      % dict(cmd=subcmd))

        # Parse all given parameters and collect their values.
        param_vals = dict([(x, {}) for x in subcmds])
        nacc_params = []
        for opstr in rawpars:
            lst = opstr.split(":", 1)
            lst += [None] * (2 - len(lst))
            param, strval = lst

            if param in param_vals and not scview._multivals[param]:
                error(_p_("error in command line (subcommand)",
                         "parameter '%(par)s' repeated more than once")
                       % dict(par=param))

            param_accepted = False
            for subcmd in subcmds:
                scview = self._scviews[subcmd]
                if param not in scview._ptypes:
                    # Current subcommand does not have this parameter, skip.
                    continue

                ptype = scview._ptypes[param]
                if ptype is bool and strval is not None:
                    error(_p_("error in command line (subcommand)",
                             "parameter '%(par)s' is a flag, no value expected")
                          % dict(par=param))
                if ptype is not bool and strval is None:
                    error(_p_("error in command line (subcommand)",
                             "value expected for parameter '%(par)s'")
                          % dict(par=param))

                val = scview._defvals[param]
                if ptype is bool:
                    val = not val

                val_lst = []
                if strval is not None:
                    if not scview._seplists[param]:
                        try:
                            val = ptype(strval)
                        except:
                            error(_p_("error in command line (subcommand)",
                                     "cannot convert value '%(val)s' to "
                                     "parameter '%(par)s' into expected "
                                     "type '%(type)s'")
                                  % dict(val=strval, par=param, type=ptype))
                        val_lst = [val]
                    else:
                        tmplst = strval.split(",")
                        try:
                            val = [ptype(x) for x in tmplst]
                        except:
                            error(_p_("error in command line (subcommand)",
                                     "cannot convert value '%(val)s' to "
                                     "parameter '%(par)s' into list of "
                                     "elements of expected type '%(type)s'")
                                  % dict(val=strval, par=param, type=ptype))
                        val_lst = val

                # Assure admissibility of parameter values.
                admvals = scview._admvals[param]
                if admvals is not None:
                    for val in val_lst:
                        if val not in admvals:
                            avals = self._fmt_admvals(admvals)
                            error(_p_("error in command line (subcommand)",
                                     "value '%(val)s' to parameter '%(par)s' "
                                     "not from the admissible set: %(avals)s")
                                  % dict(val=strval, par=param, avals=avals))

                param_accepted = True
                if scview._multivals[param] or scview._seplists[param]:
                    if param not in param_vals[subcmd]:
                        param_vals[subcmd][param] = []
                    param_vals[subcmd][param].extend(val_lst)
                else:
                    param_vals[subcmd][param] = val

            if not param_accepted and param not in nacc_params:
                nacc_params.append(param)

        if abort:
            error(_p_("error in command line (subcommand)",
                     "parameters not expected by any of the "
                     "issued subcommands: %(pars)s")
                  % dict(pars=" ".join(nacc_params)))

        # Assure that all mandatory parameters have been supplied to each
        # issued subcommand, and set defaults for all optional parameters.
        for subcmd in subcmds:
            scview = self._scviews[subcmd]

            for param in scview._ptypes:
                if param in param_vals[subcmd]:
                    # Option explicitly given, skip.
                    continue

                if scview._mandatorys[param]:
                    error(_p_("error in command line (subcommand)",
                             "mandatory parameter '%(par)s' to subcommand "
                             "'%(cmd)s' not given")
                          % dict(par=param, cmd=subcmd))

                param_vals[subcmd][param] = scview._defvals[param]

        # Create dictionary of parameter objects.
        class ParamsTemp (object): pass
        params = {}
        for subcmd in subcmds:
            params[subcmd] = ParamsTemp()
            for param, val in param_vals[subcmd].iteritems():
                # Construct valid attribute name out of parameter name.
                to_attr_rx = re.compile(r"[^a-z0-9]+", re.I|re.U)
                attr = scview._attrnames[param]
                if not attr:
                    attr = to_attr_rx.sub("_", param)
                    if not attr[:1].isalpha():
                        attr = "x" + attr
                params[subcmd].__dict__[attr] = val

        return params, nacc_params


    def _fmt_admvals (self, admvals, delim=" "):

        lst = []
        for aval in admvals:
            aval_str = str(aval)
            if aval_str != "":
                lst.append(aval_str)
            else:
                lst.append(_p_("name for an empty string as parameter value",
                              "<empty>"))
        return delim.join(lst)


class SubcmdView (object):
    """
    The view of a particular subcommand in a parameter parser.
    """

    def __init__ (self, parent, subcmd, desc=None, shdesc=None):
        """
        Constructor.

        @param parent: the parent parameter parser.
        @type parent: L{ParamParser}
        @param subcmd: subcommand name
        @type subcmd: string
        @param desc: subcommand description
        @type desc: string
        @param shdesc: short subcommand description
        @type shdesc: string
        """

        self._parent = parent
        self._subcmd = subcmd
        self._desc = desc
        self._shdesc = shdesc

        # Maps by parameter name.
        self._ptypes = {}
        self._mandatorys = {}
        self._defvals = {}
        self._admvals = {}
        self._multivals = {}
        self._seplists = {}
        self._metavars = {}
        self._descs = {}
        self._attrnames = {}

        # Parameter names in the order in which they were added.
        self._ordered = []


    def set_desc (self, desc):
        """
        Set description of the subcommand.
        """

        self._desc = desc


    def set_shdesc (self, shdesc):
        """
        Set short description of the subcommand.
        """

        self._shdesc = shdesc


    def add_param (self, name, ptype, mandatory=False, attrname=None,
                   defval=None, admvals=None, multival=False, seplist=False,
                   metavar=None, desc=None):
        """
        Define a parameter.

        A parameter is at minimum defined by its name and value type,
        and may be optional or mandatory. Optional parameter will be set
        to the supplied default value if not encountered during parsing.

        Default value must be of the given parameter type (in the sense of
        C{isinstance()}) or C{None}. Default value of C{None} can be used
        to be able to check if the parameter has been parsed at all.
        If parameter type is boolean, then the default value has a special
        meaning: the parameter is always parsed without an argument (a flag),
        and its value will become negation of the default value.
        If parameter value is not arbitrary for the given type, the set
        of admissible values can be defined too.

        Parameter can be used to collect a list of values, in two ways,
        or both combined. One is by repeating the parameter several times
        with different values, and another by a single parameter value itself
        being a comma-separated list of values (in which case the values are
        parsed into elements of requested type). For such parameters
        the default value should be a list too (or C{None}).

        For help purposes, parameter may be given a description and
        metavariable to represent its value.

        If the parameter being added to current subcommand has the name
        same as a previously defined parameter to another subcommand,
        then the current parameter shares semantics with the old one.
        This means that the type and list nature of current parameter must
        match that of the previous one (i.e. C{ptype}, C{multival}, and
        C{seplist} must have same values).

        Double-newline in description string splits text into paragraphs.

        @param name: parameter name
        @type name: string
        @param ptype: type of the expected argument
        @type ptype: type
        @param mandatory: whether parameter is mandatory
        @type mandatory: bool
        @param attrname: explicit name for the object attribute under which
            the parsed parameter value is stored (auto-derived if C{None})
        @type attrname: string
        @param defval: default value for the argument
        @type defval: instance of C{ptype} or C{None}
        @param admvals: admissible values for the argument
        @type admvals: list of C{ptype} elements or C{None}
        @param multival: whether parameter can be repeated for list of values
        @type multival: bool
        @param seplist: whether parameter is a comma-separated list of values
        @type seplist: bool
        @param metavar: name for parameter's value
        @type metavar: string or C{None}
        @param desc: description of the parameter
        @type desc: string or C{None}
        """

        param = name
        islist = multival or seplist

        if defval is not None and not islist and not isinstance(defval, ptype):
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to "
                     "subcommand '%(cmd)s' with default value '%(val)s' "
                     "different from its stated type '%(type)s'")
                  % dict(par=param, cmd=self._subcmd, val=defval, type=ptype))

        if defval is not None and islist and not _isinstance_els(defval, ptype):
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to "
                     "subcommand '%(cmd)s' with default value '%(val)s' "
                     "which contains some elements different from their "
                     "stated type '%(type)s'")
                  % dict(par=param, cmd=self._subcmd, val=defval, type=ptype))

        if defval is not None and admvals is not None and defval not in admvals:
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to "
                     "subcommand '%(cmd)s' with default value '%(val)s' "
                     "not from the admissible set: %(avals)s")
                  % dict(par=param, cmd=self._subcmd, val=defval,
                         avals=self._parent._fmt_admvals(admvals)))

        if param in self._ptypes:
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to subcommand "
                     "'%(cmd)s' once again")
                  % dict(par=param, cmd=self._subcmd))

        if islist and not isinstance(defval, (type(None), tuple, list)):
            error(_p_("error message",
                     "parameter '%(par)s' to subcommand '%(cmd)s' "
                     "stated to be list-valued, but the default value "
                     "is not given as a list or tuple")
                  % dict(par=param, cmd=self._subcmd))

        general_ptype = None
        general_multival = None
        general_seplist = None
        for scview in self._parent._scviews.itervalues():
            general_ptype = scview._ptypes.get(param)
            general_multival = scview._multivals.get(param)
            general_seplist = scview._seplists.get(param)

        if general_ptype is not None and ptype is not general_ptype:
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to "
                     "subcommand '%(cmd)s' with 'ptype' field "
                     "different from other subcommands")
                  % dict(par=param, cmd=self._subcmd))

        if general_multival is not None and multival != general_multival:
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to "
                     "subcommand '%(cmd)s' with 'multival' field "
                     "different from other subcommands")
                  % dict(par=param, cmd=self._subcmd))

        if general_seplist is not None and seplist != general_seplist:
            error(_p_("error message",
                     "trying to add parameter '%(par)s' to "
                     "subcommand '%(cmd)s' with a 'seplist' field "
                     "different from other subcommands")
                  % dict(par=param, cmd=self._subcmd))

        self._ptypes[param] = ptype
        self._mandatorys[param] = mandatory
        self._defvals[param] = defval
        self._admvals[param] = admvals
        self._multivals[param] = multival
        self._seplists[param] = seplist
        self._metavars[param] = metavar
        self._descs[param] = desc
        self._attrnames[param] = attrname

        self._ordered.append(param)


    def help (self, wcol=79):
        """
        Formatted help for the subcommand.

        @param wcol: column to wrap text at (<= 0 for no wrapping)
        @type wcol: int

        @return: formatted help
        @rtype: string
        """

        # Split parameters into mandatory and optional.
        m_params = []
        o_params = []
        for param in self._ordered:
            if self._mandatorys[param]:
                m_params.append(param)
            else:
                o_params.append(param)

        # Format output.

        def fmt_wrap (text, indent=""):
            wrapper = TextWrapper(initial_indent=indent,
                                  subsequent_indent=indent,
                                  width=wcol)
            paras = text.split("\n\n")
            fmtparas = []
            for para in paras:
                fmtparas.append(wrapper.fill(para))
            return "\n\n".join(fmtparas)

        def fmt_par (param, indent=""):
            s = ""
            s += indent + "  " + param
            ptype = self._ptypes[param]
            if ptype is bool:
                s += " "*1 + _p_("subcommand help: near the parameter "
                                "name, indicates the parameter is a flag",
                                "[flag]")
            else:
                metavar = self._metavars[param]
                if metavar is None:
                    metavar = _p_("subcommand help: default name for the "
                                 "parameter value; do keep uppercase",
                                 "ARG")
                s += ":%s" % metavar
            defval = self._defvals[param]
            admvals = self._admvals[param]
            if ptype is not bool and defval is not None and str(defval):
                cpos = len(s) - s.rfind("\n") - 1
                s += " "*1 + _p_("subcommand help: near the parameter name, "
                                "states the default value of its argument",
                                "[default %(arg)s=%(val)s]") \
                             % dict(arg=metavar, val=defval)
                if admvals is not None:
                    s += "\n" + (" " * cpos)
            if ptype is not bool and admvals is not None:
                avals = self._parent._fmt_admvals(admvals)
                s += " "*1 + _p_("subcommand help: near the parameter name, "
                                "states admissible values for its argument",
                                "[%(arg)s is one of: %(avals)s]") \
                             % dict(arg=metavar, avals=avals)
            s += "\n"
            desc = self._descs[param]
            if desc:
                fmt_desc = fmt_wrap(desc, indent + "      ")
                s += fmt_desc
                ## Wrap current parameter with empty lines if
                ## the description spanned several lines.
                #if "\n\n" in fmt_desc:
                   #s = "\n" + s + "\n"
                s += "\n" # empty line after description
            return s

        ls = []
        ls += ["  " + _p_("subcommand help: header", "%(cmd)s")
                      % dict(cmd=self._subcmd)]
        ls += ["  " + "=" * len(ls[-1].strip())]
        desc = self._desc
        if not desc:
            desc = _p_("subcommand help: dummy description when "
                      "the subcommand provides none",
                      "No description available.")
        ls += [fmt_wrap(desc, "    ")]

        if m_params:
            ls += [""]
            ls += ["  " + _p_("subcommand help: header",
                             "Mandatory parameters:")]
            for param in m_params:
                ls += [fmt_par(param, "  ")]

        if o_params:
            ls += [""]
            ls += ["  " + _p_("subcommand help: header",
                             "Optional parameters:")]
            for param in o_params:
                ls += [fmt_par(param, "  ")]

        return "\n".join(ls).strip("\n")


    def shdesc (self):
        """
        Get short description of the subcommand.

        Short description was either explicitly provided on construction,
        or it is taken as the first sentence of the first paragraph of
        the full description.

        @return: short description
        @rtype: string
        """

        if self._shdesc is not None:
            return self._shdesc
        else:
            p1 = self._desc.find("\n\n")
            if p1 < 0: p1 = len(self._desc)
            p2 = self._desc.find(". ")
            if p2 < 0: p2 = len(self._desc)
            shdesc = self._desc[:min(p1, p2)].strip()
            if shdesc.endswith("."):
                shdesc = shdesc[:-1]
            return shdesc


# Check if all elements in a list are instances of given type
def _isinstance_els (lst, typ):

    return reduce(lambda x, y: x and isinstance(y, typ), lst, True)


# -*- coding: UTF-8 -*-

"""
Pretty-printing of tabular data.

@author: Chusslove Illich (Часлав Илић) <caslav.ilic@gmx.net>
@license: GPLv3
"""

import copy


def tabulate (data, coln=None, rown=None, dfmt=None, space="  ", none="",
              rotated=False):
    """
    Tabulate data in plain text.

    All data fields can have missing trailing entries. They will be set to
    C{None} according to table extents.

    Examples:

        >>> print T.tabulate(data=((1, 4), (2, ), (3, 6)),
        ...                  coln=("c1", "c2", "c3"), rown=("r1", "r2"),
        ...                  space="  ", none="-")
        -   c1  c2  c3
        r1   1   2   3
        r2   4   -   6

    @param data: column entries (cells) by column
    @type data: list of lists of strings

    @param coln: column names
    @type coln: list of strings

    @param rown: row names
    @type rown: list of strings

    @param dfmt: format strings per column (e.g. C{"%+.2f"} for floats)
    @type dfmt: list of strings

    @param space: fill-in for spacing between cells
    @type space: string

    @param none: fill-in for displaying empty cells (i.e. C{None}-valued)
    @type none: string

    @param rotated: whether the table should be transposed
    @type rotated: bool

    @returns: plain text representation of the table (no trailing newline)
    @rtype: string
    """

    # Make local copies, to be able to extend to table extents.
    _data = []
    for col in data:
        _data.append(list(col))
    _coln = None
    if coln: _coln = list(coln)
    _rown = None
    if rown: _rown = list(rown)
    _dfmt = None
    if dfmt: _dfmt = list(dfmt)

    # Calculate maximum row and column number.
    # ...look at data:
    nrows = 0
    ncols = 0
    for col in _data:
        if nrows < len(col):
            nrows = len(col)
        ncols += 1
    # ...look at column and row names:
    if _coln is not None:
        if ncols < len(_coln):
            ncols = len(_coln)
    if _rown is not None:
        if nrows < len(_rown):
            nrows = len(_rown)

    # Index offsets due to column/row names.
    ro = 0
    if _coln is not None:
        ro = 1
    co = 0
    if _rown is not None:
        co = 1

    # Extend all missing table fields.
    # ...add columns:
    for c in range(len(_data), ncols):
        _data.append([])
    # ...add rows:
    for col in _data:
        for r in range(len(col), nrows):
            col.append(None)
    # ...add column names:
    if _coln is not None:
        if _rown is not None:
            _coln.insert(0, none) # header corner
        for c in range(len(_coln), ncols + co):
            _coln.append(None)
    # ...add row names:
    if _rown is not None:
        if _coln is not None:
            _rown.insert(0, none) # header corner
        for r in range(len(_rown), nrows + ro):
            _rown.append(None)
    # ...add formats:
    if _dfmt is None:
        _dfmt = []
    if _rown is not None:
        _dfmt.insert(0, u"%s") # header corner
    for c in range(len(_dfmt), ncols + co):
        _dfmt.append(u"%s")

    # Stringize data.
    # ...nice fat deep assembly of empty stringized table:
    sdata = [[u"" for i in range(nrows + ro)] for j in range(ncols + co)]
    # ...table body:
    for c in range(ncols):
        for r in range(nrows):
            if _data[c][r] is not None:
                sdata[c + co][r + ro] = _dfmt[c + co] % (_data[c][r],)
            else:
                sdata[c + co][r + ro] = none
    # ...column names:
    if _coln is not None:
        for c in range(ncols + co):
            if _coln[c] is not None:
                sdata[c][0] = u"%s" % (_coln[c],)
    # ...row names:
    if _rown is not None:
        for r in range(nrows + ro):
            if _rown[r] is not None:
                sdata[0][r] = u"%s" % (_rown[r],)

    # Rotate needed data for output.
    if rotated:
        _coln, _rown = _rown, _coln
        ncols, nrows = nrows, ncols
        co, ro = ro, co
        sdata_r = [[u"" for i in range(nrows + ro)] for j in range(ncols + co)]
        for c in range(ncols + co):
            for r in range(nrows + ro):
                sdata_r[c][r] = sdata[r][c]
        sdata = sdata_r

    # Calculate maximum lengths per screen column.
    maxlen = [0] * (ncols + co)
    for c in range(ncols + co):
        for r in range(nrows + ro):
            l = len(sdata[c][r])
            if maxlen[c] < l:
                maxlen[c] = l

    # Reformat strings to maximum length per column.
    for c in range(co, ncols + co):
        lfmt = u"%" + str(maxlen[c]) + "s"
        for r in range(ro, nrows + ro):
            sdata[c][r] = lfmt % (sdata[c][r],)
        # ...but column names left aligned:
        if _coln is not None:
            lfmt = u"%-" + str(maxlen[c]) + "s"
            sdata[c][0] = lfmt % (sdata[c][0],)
    # ...but row names left aligned:
    if _rown is not None:
        lfmt = u"%-" + str(maxlen[0]) + "s"
        for r in range(nrows + ro):
            sdata[0][r] = lfmt % (sdata[0][r],)

    # Assemble the table.
    lines = []
    for r in range(nrows + ro):
        cells = []
        for c in range(ncols + co):
            cells.append(sdata[c][r])
        lines.append(space.join(cells))

    return "\n".join(lines)

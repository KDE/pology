#!/bin/sh
# Generate API documentation from Python sources with the Epydoc tool.

function exit_usage ()
{
    cmd=`basename $0`
    echo "\
Usage:
  $cmd PYPKGDIR HTMLOUTDIR"
    exit 100
}

pypkgdir=$1
test -n "$pypkgdir" || exit_usage
htmldir=$2
test -n "$pypkgdir" || exit_usage

if test x`which epydoc` = x; then
    echo "\
Epydoc not found. Install it from Epydoc website at http://epydoc.sf.net,
or use your distribution package (apt-get install python-epydoc or
yum install epydoc)."
    exit 1
fi

# Proper module path for epydoc to follow.
export PYTHONPATH=$pypkgdir:$PYTHONPATH

rm -rf $htmldir/*
find $pypkgdir -iname \*.pyc | xargs -r rm

epydoc pology \
       -o $htmldir -v \
       --no-sourcecode --no-frames --no-private \
       --exclude=external --exclude=internal

# Kill generation timestamps, to not have diffs just due to it.
  find $htmldir -iname \*.html \
| xargs perl -pi -e 's/(Generated\b.*?) *on\b.*?(<|$)/$1$2/'

# Peform repository ops.
if test -d $htmldir/.svn; then
    svn status $htmldir | grep '^!' | sed 's/.//' | xargs -r svn rm
    svn status $htmldir | grep '^?' | sed 's/.//' | xargs -r svn add
fi

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

epydoc=${EPYDOC_EXECUTABLE:-epydoc}
if test -z "`which $epydoc`"; then
    echo "Epydoc (http://epydoc.sf.net) not found."
    exit 1
fi

rm -rf $htmldir/*
find $pypkgdir -iname \*.pyc | xargs -r rm
epydoc $pypkgdir/pology/ \
       -o $htmldir -v \
       --no-sourcecode --no-frames --no-private \
       --exclude=external --exclude=internal

# Peform repository ops.
if test -d $htmldir/.svn; then
    # Kill generation timestamps, in order not to have diffs just due to it.
    find $htmldir -iname \*.html \
        | xargs perl -pi -e 's/(Generated\b.*?) *on\b.*?(<|$)/$1$2/'
    svn status $htmldir | grep '^!' | sed 's/.//' | xargs -r svn rm
    svn status $htmldir | grep '^?' | sed 's/.//' | xargs -r svn add
fi

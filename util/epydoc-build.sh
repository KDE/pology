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

rm -rf $htmldir && mkdir -p $htmldir
find $pypkgdir -iname \*.pyc | xargs -r rm
epydoc $pypkgdir/pology/ \
       -o $htmldir -v \
       --no-sourcecode --no-frames --no-private \
       --exclude=external --exclude=internal


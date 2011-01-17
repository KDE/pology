#!/bin/sh
# Generate API documentation from Python sources with the Epydoc tool

cd $(dirname $0)

if test x`which epydoc` = x; then
    echo "Epydoc not found. Please install it from Epydoc website : http://epydoc.sf.net"
    echo "or use your distribution package (apt-get install python-epydoc or yum install epydoc)"
    exit 1
fi

# Proper module path for epydoc to follow.
export PYTHONPATH=../../pology:$PYTHONPATH

htmldir=../../doc-html/user/en_US

rm -rf $htmldir/*
find ../../ -iname \*.pyc | xargs -r rm

epydoc pology \
       -o $htmldir -v \
       --no-sourcecode --no-frames --no-private --exclude=external

# Kill generation timestamps, to not have diffs just due to it.
  find $htmldir -iname \*.html \
| xargs perl -pi -e 's/(Generated\b.*?) *on\b.*?(<|$)/$1$2/'

# Peform repository ops.
svn status $htmldir | grep '^!' | sed 's/.//' | xargs -r svn rm
svn status $htmldir | grep '^?' | sed 's/.//' | xargs -r svn add

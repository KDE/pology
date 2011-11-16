#!/bin/sh

cd $(dirname $0)
srcdir=..

if test -n "$1"; then
    dstdir=$1
    if test -z "$2"; then
        echo "If destination directory is given in command line, "\
             "server root must be given as well."
        exit 1
    fi
    srvroot=$2
else
    # Expects www-pology entry in SSH config.
    dstdir=www-pology:pology.nedohodnik.net
    srvroot=http://pology.nedohodnik.net
fi
if test -n "$3"; then
    builddoc=$3
else
    builddoc=1
fi

echo "Copying base files..."
cp -aLf base tmpwww
find tmpwww -type f | xargs sed -i -r "s|@srvroot@|$srvroot|g"

if test ! $builddoc = 0; then
    echo "Building local documentation:"
    rm -rf $srcdir/doc-html
    echo "- user manual..."
    $srcdir/doc/user/local.sh build
    echo "- language support manuals..."
    for local in $srcdir/lang/*/doc/local.sh; do
        $local build || exit 1
    done
    echo "- API documentation..."
    $srcdir/doc/api/local.sh build
fi
cp -aL $srcdir/doc-html/* tmpwww/doc/

echo "Syncing with web site..."
# Expects www-pology entry in SSH config.
rsync -rav --delete --cvs-exclude tmpwww/ $dstdir/
rm -rf tmpwww

echo "All done."

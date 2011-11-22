#!/bin/sh

scriptdir=$(dirname $0)
cd $scriptdir

srcdir=..

if test -n "$1"; then
    relsrcdir="$(revpath $scriptdir)/$1"
else
    relsrcdir=
fi

if test -n "$2"; then
    dstdir=$2
    if test -z "$3"; then
        echo "If destination directory is given in command line,"
             "server root must be given as well."
        exit 1
    fi
    srvroot=$3
else
    # Expects www-pology entry in SSH config.
    dstdir=www-pology:pology.nedohodnik.net
    srvroot=http://pology.nedohodnik.net
fi

echo "Copying base files..."
cp -aLf base tmpwww
find tmpwww -type f | xargs grep -lI '@srvroot@' \
| xargs sed -i -r "s|@srvroot@|$srvroot|g"

if test -n "$relsrcdir"; then
    echo "Building release documentation:"
    rm -rf $relsrcdir/doc-html
    echo "- user manual..."
    $relsrcdir/doc/user/local.sh build
    echo "- language support manuals..."
    for locbld in $relsrcdir/lang/*/doc/local.sh; do
        $locbld build || exit 1
    done
    echo "- API documentation..."
    $relsrcdir/doc/api/local.sh build
    cp -aL $srcdir/doc-html/* tmpwww/doc/
    excldoc=
else
    excldoc="--exclude doc/"
fi

echo "Syncing with web site..."
rsync -rav --delete \
      --cvs-exclude --exclude release/ $excldoc \
      tmpwww/ $dstdir/
rm -rf tmpwww

echo "All done."

#!/bin/sh

cd $(dirname $0)
srcdir=..

echo "Copying base files..."
cp -aLf base tmpwww

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
cp -aL $srcdir/doc-html/* tmpwww/doc/

echo "Syncing with web site..."
# Expects www-pology entry in SSH config.
rsync -rav --delete --cvs-exclude tmpwww/ www-pology:pology.nedohodnik.net/
rm -rf tmpwww

echo "All done."

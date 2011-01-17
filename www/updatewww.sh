#!/bin/sh

cd $(dirname $0)

cp -aLf base tmpwww
cp -aLf ../doc-html/* tmpwww/doc/
# Expects www-pology entry in SSH config.
rsync -rav --delete --cvs-exclude tmpwww/ www-pology:pology.nedohodnik.net/
rm -rf tmpwww

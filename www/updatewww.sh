#!/bin/sh

cd $(dirname $0)

cp -a base tmpwww
ln -s ../../doc-html tmpwww/doc
# Expects www-pology entry in SSH config.
rsync -raLv --delete --cvs-exclude tmpwww/ www-pology:pology.nedohodnik.net/
rm -rf tmpwww

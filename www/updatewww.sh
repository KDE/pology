#!/bin/sh

cd $(dirname $0)

cp -a base tmpwww
mkdir tmpwww/doc
ln -s ../../../doc/user/html tmpwww/doc/user
ln -s ../../../doc/api/html tmpwww/doc/api
# Expects www-pology entry in SSH config.
rsync -raLv --delete --cvs-exclude tmpwww/ www-pology:pology.nedohodnik.net/
rm -rf tmpwww

#!/bin/sh

mkdir tmpwww
mkdir tmpwww/doc
ln -s ../../../doc/user/html tmpwww/doc/user
ln -s ../../../doc/api/html tmpwww/doc/api
touch -d 2010-12-07 tmpwww/favicon.gif tmpwww/favicon.ico
echo '<?php header("Location: http://pology.nedohodnik.net/doc/user/");?>' > tmpwww/index.php
touch -d 2010-12-07 tmpwww/index.php
# Expects www-pology entry in SSH config.
rsync -raLv --delete --cvs-exclude tmpwww/ www-pology:pology.nedohodnik.net/
rm -rf tmpwww

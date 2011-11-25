#!/bin/sh

# Usage:
#
#   make-release-tarball.sh <VERSION>
#
# Can be run from any directory.

version=$1

cmddir=`dirname $0`

if test -z "$version"; then
    version=$(cat $cmddir/../VERSION)
    echo "Version number: $version (from VERSION)"
else
    echo $version >VERSION
    echo "Version number: $version (manually given)"
fi

pkgname=pology-$version

echo "Creating tarball directory..."
tdir=/tmp/$pkgname
rm -rf $tdir
cp -r $cmddir/.. $tdir
# All following actions happen in tarball directory.
cd $tdir

echo "Removing non-distributed files..."
find -iname \.svn | xargs rm -rf
find -iname \*.pyc | xargs rm -rf
find -iname \*.sdc | xargs rm -rf
rm -rf build
rm -rf doc-html
rm -rf mo
rm -rf www

echo "Making tarball..."
cd ..
pkgpath=`dirname $tdir`/$pkgname.tar.bz2
tar -cjf $pkgpath $pkgname

echo "Tarball ready at: $pkgpath"

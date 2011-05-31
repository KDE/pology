#!/bin/sh

# Usage:
#
#   make-release-tarball.sh <VERSION>
#
# Can be run from any directory.

version=$1
if test -z "$version"; then
    echo "Version number not given."
    exit 1
fi

#branch=`echo $version | sed -r 's/\.[0-9]+$//'`
#if test $branch = $version; then
#    echo "Malformed version string '$version'."
#    echo 1
#fi

date=`date -I`

pkgname=pology-$version

echo "Creating tarball directory..."
pdir=`dirname $0`
tdir=/tmp/$pkgname
rm -rf $tdir
cp -r $pdir $tdir
# All following actions happen in tarball directory.
cd $tdir

echo "Updating version information in files..."
echo $version >VERSION
sed -r '/^\s*Version\s+\S+-dev:\s*$/d' NEWS >NEWS.tail
if cmp -s NEWS NEWS.tail; then
    echo "Malformed NEWS file."
    echo 1
fi
cat >NEWS.head <<EOF
Version $version, $date:
EOF
cat NEWS.head NEWS.tail >NEWS
rm NEWS.head NEWS.tail

echo "Removing repository bookkeeping..."
find -iname \.svn | xargs rm -rf
rm `basename $0` # i.e. this script

echo "Removing transient files..."
find -iname \.svn | xargs rm -rf
find -iname \*.pyc | xargs rm -rf
find -iname \*.sdc | xargs rm -rf

echo "Removing experimental stuff..."
rm scripts/poextinj.py bin/poextinj
rm scripts/podescprob.py bin/podescprob

echo "Regenerating API documentation..."
doc/api/makedoc.sh || exit 1
echo "Regenerating user manual..."
doc/user/makedoc.sh || exit 1

echo "Updating translations..."
po/pology/update-po.sh || exit 1
rm -rf mo

echo "Making tarball..."
cd ..
pkgpath=`dirname $tdir`/$pkgname.tar.bz2
tar -cjf $pkgpath $pkgname

echo "Tarball ready at: $pkgpath"

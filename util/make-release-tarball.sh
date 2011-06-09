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
cmddir=`dirname $0`
tdir=/tmp/$pkgname
rm -rf $tdir
cp -r $cmddir/.. $tdir
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

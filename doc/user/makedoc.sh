#/bin/sh

cd $(dirname $0)

mode=$1

topdbk=top.docbook

xmllint --noout --xinclude --postvalid $topdbk || exit 1

test "$mode" = "check" && exit 0

htmldir=../../doc-html/user/en_US
revdir=../../../doc/user

rm -rf $htmldir/*; mkdir -p $htmldir
ln -s $revdir/html-data $htmldir/data
xsltproc --xinclude html-mono.xsl $topdbk >$htmldir/index-mono.html
xsltproc --xinclude html-chapters.xsl $topdbk && mv html/* $htmldir && rmdir html
tidy -q --show-warnings no -utf8 -w 0 -m $htmldir/*.html; test -z
# Remove title= attributes to sectioning classes,
# because they cause a tooltip to be shown wherever the pointer is.
perl -pi -e 's/(<div[^>]*?class="(abstract|article|book|chapter|sect)[^>]*?) *title=".*?"/\1/' $htmldir/*.html

if test -d $htmldir/.svn; then
    svn status $htmldir | grep '^!' | sed 's/.//' | xargs -r svn rm
    svn status $htmldir | grep '^?' | sed 's/.//' | xargs -r svn add
fi

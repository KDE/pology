#/bin/sh

function exit_usage ()
{
    cmd=`basename $0`
    echo "\
Usage:
  $cmd TOPDBKFILE HTMLOUTDIR"
    exit 100
}

topdbk=$1
test -n "$topdbk" || exit_usage
htmldir=$2
test -n "$htmldir" || exit_usage

cmddir=`dirname $0`
$cmddir/docbook-check.sh $topdbk || exit 1

rm -rf $htmldir/*; mkdir -p $htmldir
cp $cmddir/docbook-html-style.css $htmldir/style.css
xsltproc --xinclude $cmddir/docbook-html-mono.xsl $topdbk >$htmldir/index-mono.html
xsltproc --xinclude $cmddir/docbook-html-chapters.xsl $topdbk && mv html/* $htmldir && rmdir html
tidy -q --show-warnings no -utf8 -w 0 -m $htmldir/*.html; test -z
# Remove title= attributes to sectioning classes,
# because they cause a tooltip to be shown wherever the pointer is.
perl -pi -e 's/(<div[^>]*?class="(abstract|article|book|chapter|sect)[^>]*?) *title=".*?"/\1/' $htmldir/*.html

if test -d $htmldir/.svn; then
    svn status $htmldir | grep '^!' | sed 's/.//' | xargs -r svn rm
    svn status $htmldir | grep '^?' | sed 's/.//' | xargs -r svn add
fi

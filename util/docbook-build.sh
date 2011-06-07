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

# Build HTML pages.
xsltproc=${XSLTPROC_EXECUTABLE:-xsltproc}
if test -z "`which $xsltproc`"; then
    echo "xsltproc (http://xmlsoft.org/) not found."
    exit 1
fi
$xsltproc --xinclude $cmddir/docbook-html-mono.xsl $topdbk >$htmldir/index-mono.html
$xsltproc --xinclude $cmddir/docbook-html-chapters.xsl $topdbk \
    && mv html/* $htmldir && rmdir html

# Sanitize HTML pages.
tidy=${TIDY_EXECUTABLE:-tidy}
if test -z "`which $tidy`"; then
    echo "Tidy (http://tidy.sourceforge.net/) not found, but continuing."
    exit 1
fi
if test -n "`which tidy`"; then
    tidy -q --show-warnings no -utf8 -w 0 -m $htmldir/*.html; test -z
fi
# Remove title= attributes to sectioning classes,
# because they cause a tooltip to be shown wherever the pointer is.
perl=${PERL_EXECUTABLE:-perl}
$perl -pi -e 's/(<div[^>]*?class="(abstract|article|book|chapter|sect)[^>]*?) *title=".*?"/\1/' $htmldir/*.html

# Copy HTML data.
dbkdir=`dirname $topdbk`
cp $cmddir/docbook-html-style.css $htmldir/style.css
find $dbkdir -maxdepth 1 \
    -iname '*.png' -o \
    -iname '*.jpg' -o \
    -name DUMMY | xargs -r cp -t $htmldir

if test -d $htmldir/.svn; then
    svn status $htmldir | grep '^!' | sed 's/.//' | xargs -r svn rm
    svn status $htmldir | grep '^?' | sed 's/.//' | xargs -r svn add
fi

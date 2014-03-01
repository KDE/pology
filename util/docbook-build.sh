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

rm -rf $htmldir && mkdir -p $htmldir

# Build HTML pages.
xsltproc=${XSLTPROC_EXECUTABLE:-xsltproc}
if test -z "`which $xsltproc`"; then
    echo "xsltproc (http://xmlsoft.org/) not found."
    exit 1
fi
# - find Docbook XSL stylesheets and configure style sheet extensions.
dbxsldir=
for adir in \
    $DOCBOOK_XSL_DIR \
    share/xml/docbook/stylesheet/docbook-xsl \
    share/xml/docbook/xsl-stylesheets \
    share/sgml/docbook/xsl-stylesheets \
    share/xml/docbook/stylesheet/nwalsh/current \
    share/xml/docbook/stylesheet/nwalsh \
    share/xsl/docbook \
    share/xsl/docbook-xsl \
; do
    for tdir in /usr /usr/local; do
        if test -f $tdir/$adir/lib/lib.xsl; then
            dbxsldir=$tdir/$adir
            break
        fi
    done
    test -n "$dbxsldir" && break
done
if test -z "$dbxsldir"; then
    echo "Docbook XSL stylesheets not found in usual paths."
    if test -z "$DOCBOOK_XSL_DIR"; then
        echo "(If they are installed elsewhere," \
             "set DOCBOOK_XSL_DIR environment variable to that path.)"
    fi
    exit 1
fi
for xslfile in docbook-html-mono.xsl docbook-html-chapters.xsl; do
    xslpath=$cmddir/$xslfile
    xslpath1=$cmddir/${xslfile/.xsl/-tmp.xsl}
    sed "s;@CONFIG_DBXSLDIR@;$dbxsldir;g" $xslpath >$xslpath1
done
# - build doc
$xsltproc --xinclude $cmddir/docbook-html-mono-tmp.xsl $topdbk >$htmldir/index-mono.html
$xsltproc --xinclude $cmddir/docbook-html-chapters-tmp.xsl $topdbk \
    && mv html/* $htmldir && rmdir html
# - add highlighting
# This relies on custom XSLT of <programlisting> in local.xsl,
# which adds <!-- language: ... --> comment.
# Highlighting CSS definitions are also in docbook-html-style.css.
$cmddir/add-html-highlight.py $htmldir/*

# - clean up
rm $cmddir/*-tmp.xsl

# Sanitize HTML pages.
tidy=${TIDY_EXECUTABLE:-tidy}
if test -n "`which $tidy`"; then
    tidy -q --show-warnings no -utf8 -w 0 -m $htmldir/*.html; test -z
fi
# Remove title= attributes to sectioning classes,
# because they cause a tooltip to be shown wherever the pointer is.
sed -i -r 's/(<div[^>]* class="(abstract|article|book|chapter|sect)[^>]*) title="[^"]*"/\1/g' $htmldir/*.html

# Copy HTML data.
dbkdir=`dirname $topdbk`
cp $cmddir/docbook-html-style.css $htmldir/style.css
find $dbkdir -maxdepth 1 \
    -iname '*.png' -o \
    -iname '*.jpg' -o \
    -name DUMMY | xargs -r cp -t $htmldir


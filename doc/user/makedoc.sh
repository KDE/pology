#/bin/sh

cd $(dirname $0)

mode=$1

topdbk=top.docbook

xmllint --noout --xinclude --postvalid $topdbk || exit 1

test "$mode" = "check" && exit 0

rm -rf html/*; mkdir -p html
ln -s ../html-data html/data
xsltproc --xinclude html-mono.xsl $topdbk >html/index-mono.html
xsltproc --xinclude html-chapters.xsl $topdbk
tidy -q --show-warnings no -utf8 -w 0 -m html/*.html; test -z

svn status html/ | grep '^!' | sed 's/.//' | xargs -r svn rm
svn status html/ | grep '^?' | sed 's/.//' | xargs -r svn add

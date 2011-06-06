#!/bin/sh

mode=$1

cd $(dirname $0)
utildir=../../../util
topdbk=top.docbook
htmldir=../../../doc-html/lang/sr/sr

case "$mode" in
build)
    $utildir/docbook-build.sh $topdbk $htmldir
    ;;
check)
    $utildir/docbook-check.sh $topdbk
    ;;
*)
    echo -e "Usage:\n  $(basename $0) [build|check]"
    exit 1
esac

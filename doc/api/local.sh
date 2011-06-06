#!/bin/sh

mode=$1

cd $(dirname $0)
utildir=../../util
pypkgdir=../..
htmldir=../../doc-html/api/en_US

case "$mode" in
build)
    $utildir/epydoc-build.sh $pypkgdir $htmldir
    ;;
*)
    echo -e "Usage:\n  $(basename $0) build"
    exit 1
esac

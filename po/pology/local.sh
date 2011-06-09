#!/bin/sh

mode=$1
lang=$2

cd $(dirname $0)

case "$mode" in
build)
    ./update-po.sh compile $lang
    ;;
*)
    echo -e "Usage:\n  $(basename $0) build [lang]"
    exit 1
esac

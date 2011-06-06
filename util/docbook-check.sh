#!/bin/sh

function exit_usage ()
{
    cmd=`basename $0`
    echo "\
Usage:
  $cmd TOPDBKFILE
"
    exit 100
}

topdbk=$1
test -n "$topdbk" || exit_usage

xmllint --noout --xinclude --postvalid $topdbk || exit 1

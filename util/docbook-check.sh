#!/bin/sh

function exit_usage ()
{
    cmd=`basename $0`
    echo "\
Usage:
  $cmd TOPDBKFILE"
    exit 100
}

topdbk=$1
test -n "$topdbk" || exit_usage

xmllint=${XMLLINT_EXECUTABLE:-xmllint}
if test -z "`which $xmllint`"; then
    echo "xmllint (http://xmlsoft.org/) not found."
    exit 1
fi
$xmllint --noout --xinclude --postvalid $topdbk || exit 1

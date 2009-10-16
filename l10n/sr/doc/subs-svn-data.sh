#!/bin/sh

file=$1

dfmt="+%-d. %B %Y."

bldate=`date "$dfmt"`

vcsdate=`svn info --xml $file | grep '<text-updated>' \
         | sed 's/^[^>]*>\([^T]*\).*/\1/'`
vcsdate=`date -d $vcsdate "$dfmt"`

vcsrev=`svn info --xml $file | grep 'revision=' | tail -1 \
        | sed 's/^.*"\([^"]*\)".*/\1/'`

sed <$file >$file.tmp\
    -e "s/@bldate@/$bldate/" \
    -e "s/@vcsdate@/$vcsdate/" \
    -e "s/@vcsrev@/$vcsrev/" \

echo $file.tmp

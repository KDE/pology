#!/bin/sh

wdir=`pwd`
cdir=`dirname $0`
podomain=pology

mode=all
if test -n "$1"; then
    mode=$1
fi
onelang=
if test -n "$2"; then
    onelang=$2
fi

if [[ :all:extract:test:compile: != *:$mode:* ]]; then
    echo "*** Unknown mode '$mode'."
    echo "*** (Known modes: all, extract, merge, compile.)"
    exit 1
fi

if test $mode = all || test $mode = extract; then
    echo ">>> Extracting template..."
    cd $cdir/../..
    # Do not just look for all *.py, keep some ordering.
    srcfiles_lib=`find pology -maxdepth 1 -iname \*.py | sort`
    srcfiles_libpr=`find pology/proj/* -maxdepth 1 -iname \*.py | sort`
    srcfiles_liblg=`find pology/lang/* -maxdepth 1 -iname \*.py | sort`
    srcfiles_libin=`find pology/internal/* -maxdepth 1 -iname \*.py | sort`
    srcfiles_script=`find scripts -maxdepth 1 -iname \*.py | sort`
    srcfiles_scriptlg=`find lang -iname \*.py | grep /scripts/ | sort`
    srcfiles_sieve=`find sieve -maxdepth 1 -iname \*.py | sort`
    srcfiles_sievelg=`find lang -iname \*.py | grep /sieve/ | sort`
    srcfiles="\
        $srcfiles_lib $srcfiles_libpr $srcfiles_liblg $srcfiles_libin \
        $srcfiles_script $srcfiles_scriptlg \
        $srcfiles_sieve $srcfiles_sievelg \
    "
    potfile=po/$podomain/$podomain.pot
    xgettext --no-wrap \
        -k_:1c,2 -kn_:1c,2,3 -kt_:1c,2 -ktn_:1c,2,3 \
        -o $potfile $srcfiles
    cd $wdir
fi

if test $mode = all || test $mode = merge; then
    echo ">>> Merging catalogs..."
    potfile=$cdir/$podomain.pot
    if [ -z "$onelang" ]; then
        langs=`cat $cdir/LINGUAS | sed 's/#.*//'`
    else
        langs=$onelang
    fi
    for lang in $langs; do
        pofile=$cdir/$lang.po
        if test ! -f $pofile; then
            echo "--- $pofile is missing."
            continue
        fi
        echo -n "$pofile  "
        msgmerge -U --backup=none --no-wrap --previous $pofile $potfile
    done
fi

if test $mode = all || test $mode = compile; then
    echo ">>> Compiling catalogs..."
    modir=$cdir/../../mo
    # Remove old compiled dir if in pristine state, otherwise warn and exit.
    if [ -d $modir ]; then
        nonmofiles=`find $modir -type f | egrep -v '.*\.mo$'`
        if [ -n "$nonmofiles" ]; then
            echo "$nonmofiles"
            echo "*** $modir contains non-compiled files."
            echo "*** Move them or delete them, then rerun the script."
            exit 1
        fi
        rm -rf $modir
    elif [ -e $modir ]; then
        echo "*** $modir not a directory."
        echo "*** Move it or delete it, then rerun the script."
        exit 1
    fi

    if [ -z "$onelang" ]; then
        langs=`cat $cdir/LINGUAS | sed 's/#.*//'`
    else
        langs=$onelang
    fi
    for lang in $langs; do
        pofile=$cdir/$lang.po
        if test ! -f $pofile; then
            echo "--- $pofile is missing."
            continue
        fi
        echo -n "$pofile  "
        pobase=`basename $pofile`
        mosubdir=$modir/$lang/LC_MESSAGES
        mkdir -p $mosubdir
        mofile=$mosubdir/$podomain.mo
        msgfmt -c --statistics $pofile -o $mofile
    done
fi


#!/bin/sh

wdir=`pwd`
cdir=`dirname $0`
potbase=pology

mode=all
if test -n "$1"; then
    mode=$1
fi
lang=
if test -n "$2"; then
    lang=$2
fi

if test $mode = all || test $mode = extract; then
    echo ">>> Extracting template..."
    cd $cdir/../..
    # Do not just look for all *.py, keep some ordering.
    srcfiles_lib=`find pology -maxdepth 1 -iname \*.py | sort`
    srcfiles_libpr=`find pology/proj/* -maxdepth 1 -iname \*.py | sort`
    srcfiles_liblg=`find pology/lang/* -maxdepth 1 -iname \*.py | sort`
    srcfiles_script=`find scripts -maxdepth 1 -iname \*.py | sort`
    srcfiles_scriptlg=`find lang -iname \*.py | grep /scripts/ | sort`
    srcfiles_sieve=`find sieve -maxdepth 1 -iname \*.py | sort`
    srcfiles_sievelg=`find lang -iname \*.py | grep /sieve/ | sort`
    srcfiles="\
              $srcfiles_lib $srcfiles_libpr $srcfiles_liblg \
              $srcfiles_script $srcfiles_scriptlg \
              $srcfiles_sieve $srcfiles_sievelg \
             "
    potfile=po/$potbase/$potbase.pot
    xgettext --no-wrap \
        -k_:1c,2 -kn_:1c,2,3 -kt_:1c,2 -ktn_:1c,2,3 \
        -o $potfile $srcfiles
    cd $wdir
fi

if test $mode = all || test $mode = merge; then
    echo ">>> Merging catalogs..."
    potfile=$cdir/$potbase.pot
    if [ -z "$lang" ]; then
        pofiles=`find $cdir -iname \*.po`
    else
        pofiles=`find $cdir -iname $lang.po`
    fi
    for pofile in $pofiles; do
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

    if [ -z "$lang" ]; then
        pofiles=`find $cdir -iname \*.po`
    else
        pofiles=`find $cdir -iname $lang.po`
    fi
    for pofile in $pofiles; do
        echo -n "$pofile  "
        pobase=`basename $pofile`
        lang=${pobase/.po/}
        mosubdir=$modir/$lang/LC_MESSAGES
        mkdir -p $mosubdir
        mofile=$mosubdir/$potbase.mo
        msgfmt -c --statistics $pofile -o $mofile
    done
fi


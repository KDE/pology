#!/bin/sh
# Joins all the specialized dictionaries into a single one, 
# located at the parent directory.

cd `dirname $0` 
echo "personal_ws-1.1 es 9999 utf-8" > ../spell/dict.aspell 
cat *.aspell >> ../spell/dict.aspell
../../../scripts/normalize-aspell-word-list.py ../spell/dict.aspell

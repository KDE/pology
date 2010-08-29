#!/bin/sh
# Joins all the specialized dictionaries into a single one, 
# located at the parent directory.
 
echo "personal_ws-1.1 es 9999 utf-8" > ../dict.aspell 
cat *.aspell >> ../dict.aspell
../../../../scripts/organizeDict.py ../dict.aspell

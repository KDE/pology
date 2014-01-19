#!/bin/bash
raiz=~/svnroot/
rama=trunk
idioma=es
salida=~/.kde4/share/locale/$idioma/LC_MESSAGES

mkdir -p $salida

origen=$raiz/$rama/l10n-kde4/$idioma/messages
for paquete in $origen/*; do
  for archivo_e in $paquete/*.po; do
    if [ -f $archivo_e ]; then
      archivo_s=$(basename $archivo_e|sed -e s/\.po$/\.mo/)
      msgfmt $archivo_e -o $salida/$archivo_s
    fi
  done
done


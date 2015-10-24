#!/bin/bash
# 
# Corrección automática de errores en las traducciones.
# El primer parámetro es la rama ('branches/stable' o 'trunk').
# El segundo parámetro es el tipo ('messages' o 'docmessages').
# Es conveniente redireccionar la salida a un archivo.
#
PROGRAMA=~/svnroot/pology/scripts/posieve.py
RAIZ=~/svnroot-cop
IDIOMA=es
OPCION=find-messages
PARAMETROS="-s accel:& -s case"

# Quita el plural de las siglas
# Suprime «s» y «'s» al final de siglas,
# excepto cuando forman parte del nombre de un archivo o URL.

P[0]="(?<=\b[A-Z]{2})\'?s\b"	R[0]=""
P+=("(?<=\b[A-Z]{3})\'?s\b")	R+=("")
P+=("(?<=\b[A-Z]{4})\'?s\b")	R+=("")
P+=("(?<=\b[A-Z]{5})\'?s\b")	R+=("")
P+=("(?<=\b[A-Z]{6})\'?s\b")	R+=("")
P+=("(?<=\b[A-Z]{7})\'?s\b")	R+=("")
P+=("(?<=\b[A-Z]{8})\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{2};)\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{3};)\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{4};)\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{5};)\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{6};)\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{7};)\'?s\b")	R+=("")
P+=("(?<=\W\&[\w-]{8};)\'?s\b")	R+=("")

if [[ $1 != '' ]]; then
  RAMA=$1
else
  echo "Debe poner la rama ('branches/stable' o 'trunk') como primer parámetro"
  exit
fi

if [[ $2 != '' ]]; then
  SUBRAMA=$2
else
  echo "Debe poner la subrama ('l10n-kde4' o 'l10n-kf5') como segundo parámetro"
  exit
fi

if [[ $3 != '' ]]; then
  TIPO=$3
else
  echo "Debe poner el tipo ('messages' o 'docmessages') como tercer parámetro"
  exit
fi

echo "Iniciando...:" $RAMA $TIPO
ORIGEN=$RAIZ/$RAMA/$SUBRAMA/$IDIOMA/$TIPO
for PAQUETE in $ORIGEN/*; do
    if [ -d $PAQUETE ]; then
	echo "Procesando...:" $PAQUETE
	for ((I=0; I<${#P[@]}; I++)); do
	    # echo "Analizando...:" "${P[$I]}"
	    $PROGRAMA '-bR' $OPCION $PARAMETROS -s msgstr:"${P[$I]}" -s replace:"${R[$I]}" $PAQUETE
	done
    fi
done

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
#-s filter:remove/remove-literals-text -s filter:remove/remove-marlits-text -s filter:remove/remove-fmtdirs-text -s filter:remove/remove-markup-text"

# Corrección de tildes en oraciones interrogativas/admirativas
P[0]="¿cuan\b"		R[0]="¿cuán"
P+=("¿cuando\b")	R+=("¿cuándo")
P+=("¿adonde\b")	R+=("¿adónde")
P+=("¿a d[oó]nde\b")	R+=("¿adónde")
P+=("¿donde\b")		R+=("¿dónde")
P+=("¿cuantas\b")	R+=("¿cuántas")
P+=("¿cuantos\b")	R+=("¿cuántos")
P+=("¿cuales\b")	R+=("¿cuáles")
P+=("¿cual\b")		R+=("¿cuál")
P+=("¿quien\b")		R+=("¿quién")
P+=("¿quienes\b")	R+=("¿quiénes")
P+=("¿como\b")		R+=("¿cómo")
P+=("¿que\b")		R+=("¿qué")
P+=("¿porque\b")	R+=("¿por qué")
P+=("¿por que\b")	R+=("¿por qué")
P+=("¿haber\b")		R+=("¿a ver")

P+=("¡cuan\b")		R+=("¡cuán")
P+=("¡cuando\b")	R+=("¡cuándo")
P+=("¡adonde\b")	R+=("¡adónde")
P+=("¡a d[oó]nde\b")	R+=("¡adónde")
P+=("¡donde\b")		R+=("¡dónde")
P+=("¡cuantas\b")	R+=("¡cuántas")
P+=("¡cuantos\b")	R+=("¡cuántos")
P+=("¡cuales\b")	R+=("¡cuáles")
P+=("¡cual\b")		R+=("¡cuál")
P+=("¡quien\b")		R+=("¡quién")
P+=("¡quienes\b")	R+=("¡quiénes")
P+=("¡como\b")		R+=("¡cómo")
P+=("¡que\b")		R+=("¡qué")
P+=("¡porque\b")	R+=("¡por qué")
P+=("¡por que\b")	R+=("¡por qué")
P+=("¡haber\b")		R+=("¡a ver")

P+=("¿Cuan\b")		R+=("¿Cuán")
P+=("¿Cuando\b")	R+=("¿Cuándo")
P+=("¿Adonde\b")	R+=("¿Adónde")
P+=("¿A d[oó]nde\b")	R+=("¿Adónde")
P+=("¿Donde\b")		R+=("¿Dónde")
P+=("¿Cuantas\b")	R+=("¿Cuántas")
P+=("¿Cuantos\b")	R+=("¿Cuántos")
P+=("¿Cuales\b")	R+=("¿Cuáles")
P+=("¿Cual\b")		R+=("¿Cuál")
P+=("¿Quien\b")		R+=("¿Quién")
P+=("¿Quienes\b")	R+=("¿Quiénes")
P+=("¿Como\b")		R+=("¿Cómo")
P+=("¿Que\b")		R+=("¿Qué")
P+=("¿Porque\b")	R+=("¿Por qué")
P+=("¿Por que\b")	R+=("¿Por qué")
P+=("¿Haber\b")		R+=("¿A ver")

P+=("¡Cuan\b")		R+=("¡Cuán")
P+=("¡Cuando\b")	R+=("¡Cuándo")
P+=("¡Adonde\b")	R+=("¡Adónde")
P+=("¡A d[oó]nde\b")	R+=("¡Adónde")
P+=("¡Donde\b")		R+=("¡Dónde")
P+=("¡Cuantas\b")	R+=("¡Cuántas")
P+=("¡Cuantos\b")	R+=("¡Cuántos")
P+=("¡Cuales\b")	R+=("¡Cuáles")
P+=("¡Cual\b")		R+=("¡Cuál")
P+=("¡Quien\b")		R+=("¡Quién")
P+=("¡Quienes\b")	R+=("¡Quiénes")
P+=("¡Como\b")		R+=("¡Cómo")
P+=("¡Que\b")		R+=("¡Qué")
P+=("¡Porque\b")	R+=("¡Por qué")
P+=("¡Por que\b")	R+=("¡Por qué")
P+=("¡Haber\b")		R+=("¡A ver")

P+=("que hora\b")	R+=("qué hora")
P+=("Que hora\b")	R+=("Qué hora")

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

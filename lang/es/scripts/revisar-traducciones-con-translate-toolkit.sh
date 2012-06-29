#!/bin/bash
RAIZ=~/svnroot/
RAMA=trunk
IDIOMA=es
SALIDA=~/svnroot/revisiones/

case $1 in
    "filtros")
	PROGRAMA=pofilter
	PARAMETROS="--language $IDIOMA --kde"
	;;
    "terminología")
	PROGRAMA=poterminology
	PARAMETROS="--ignore-case --accelerator=&"
	;;
    *)	
	echo "El parámetro debe ser: filtros|terminología";
	exit 1
	;;
esac

for TIPO in "messages" "docmessages"; do
    ORIGEN=$RAIZ/$RAMA/l10n-kde4/$IDIOMA/$TIPO
    for PAQUETE in $ORIGEN/*; do
	if [ -d $PAQUETE ]; then
	    DESTINO=$SALIDA/$1/$TIPO/$(basename $PAQUETE)/
	    mkdir -p $DESTINO
	    $PROGRAMA $PARAMETROS $PAQUETE $DESTINO
	fi
    done
done

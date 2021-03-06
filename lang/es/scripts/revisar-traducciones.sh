#!/bin/bash
PROGRAMA=~/svnroot/pology/scripts/posieve.py
RAIZ=~/svnroot/
RAMA=trunk
IDIOMA=es
SALIDA=~/svnroot/revisiones/
RUTA_LT=/usr/share/languagetool

case $1 in
    "reglas")
		OPCION=check-rules
		PARAMETROS="-s lang:$IDIOMA -s accel:& -s env:kde";;
	"ortografía")
		OPCION=check-spell
		PARAMETROS="-s lang:$IDIOMA -s accel:& -s skip:^[A-Z0-9\W]+$";;
    "gramática")
		OPCION=check-grammar
		PARAMETROS="-s lang:$IDIOMA -s accel:&"
		java -jar $RUTA_LT/LanguageToolGUI.jar &
		sleep 5;;
    "kde4")
		OPCION=check-kde4
		PARAMETROS="";;
    "tp-kde")
		OPCION=check-tp-kde
		PARAMETROS="";;
    *)	
		echo "El parámetro debe ser: reglas|ortografía|gramática|kde4|tp-kde";
		exit 1;;
esac

for TIPO in "messages" "docmessages"; do
    ORIGEN=$RAIZ/$RAMA/l10n-kde4/$IDIOMA/$TIPO
    DESTINO=$SALIDA/$1/$TIPO
    mkdir -p $DESTINO
    for PAQUETE in $ORIGEN/*; do
	if [ -d $PAQUETE ]; then
	    $PROGRAMA '--skip-obsolete' $OPCION $PARAMETROS $PAQUETE > $DESTINO/$(basename $PAQUETE)
	fi
    done
done

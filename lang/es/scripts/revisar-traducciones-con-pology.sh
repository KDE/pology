#!/bin/bash
PROGRAMA=~/svnroot/pology/scripts/posieve.py
RAIZ=~/svnroot/
RAMA=trunk
SALIDA=~/svnroot/revisiones/
RUTA_LT=/usr/share/languagetool
IDIOMA=es

case $1 in
    "reglas")
	for i in $@;
	do
	    if [[ $i =~ ^[0-3]+$ ]];
	    then
		NIVEL=$NIVEL$i
	    elif [[ $i =~ ^(bp|cm|ff|gd|gr|gp|gk|pw|pb|pe|sp|tr|ty|ui)$ ]];
	    then
		if [[ $REGLA == "" ]];
		then
		    REGLA=$i
		else
		    REGLA=$REGLA'|'$i
		fi
	    fi
	done
	if [[ $NIVEL == "" ]];
	then
	    NIVEL='0123'
	fi
	if [[ $REGLA == "" ]];
	then
	    REGLA='..'
	fi
	echo "Niveles seleccionados:" $NIVEL "Reglas seleccionadas:" $REGLA
	OPCION=check-rules
	PARAMETROS='-s lang:'$IDIOMA' -s accel:& -s env:kde -s rulerx:^('$REGLA')\-['$NIVEL']\-';;
    "ortografía")
	OPCION=check-spell
	PARAMETROS='-s lang:'$IDIOMA' -s accel:& -s case -s skip:[A-Z]+';;
    "gramática")
	OPCION=check-grammar
	PARAMETROS='-s lang:'$IDIOMA' -s accel:&'
	java -jar $RUTA_LT/LanguageToolGUI.jar &
	sleep 5;;
    "kde4")
	OPCION=check-kde4
	PARAMETROS="";;
    "tp-kde")
	OPCION=check-tp-kde
	PARAMETROS="";;
    *)
	echo 'El parámetro debe ser: reglas|ortografía|gramática|kde4|tp-kde';
	exit 1;;
esac

for TIPO in 'messages' 'docmessages'; do
    ORIGEN=$RAIZ/$RAMA/l10n-kde4/$IDIOMA/$TIPO
    DESTINO=$SALIDA/$1/$TIPO
    mkdir -p $DESTINO
    for PAQUETE in $ORIGEN/*; do
	if [ -d $PAQUETE ]; then
	    $PROGRAMA '-bR' $OPCION $PARAMETROS $PAQUETE > $DESTINO/$(basename $PAQUETE)
	fi
    done
done

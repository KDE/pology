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
	    elif [[ $i =~ ^(bp|cm|dc|ff|gd|gr|gp|gk|pw|pb|pe|pn|sp|te|tr|ty|ui)$ ]];
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
    "regla")
	OPCION=check-rules
	PARAMETROS='-s lang:'$IDIOMA' -s accel:& -s env:kde -s rule:'$2;;
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

rm -rf $SALIDA/$1

for TIPO in 'messages' 'docmessages'; do
    echo "Iniciando...:" $TIPO
    ORIGEN=$RAIZ/$RAMA/l10n-kde4/$IDIOMA/$TIPO
    DESTINO=$SALIDA/$1/$TIPO
    mkdir -p $DESTINO
    for PAQUETE in $ORIGEN/*; do
	if [ -d $PAQUETE ]; then
	    echo "Procesando...:" $PAQUETE
	    $PROGRAMA '-bR' $OPCION $PARAMETROS $PAQUETE > $DESTINO/$(basename $PAQUETE)'.vt'
	    $PROGRAMA '-b' $OPCION $PARAMETROS $PAQUETE > $DESTINO/$(basename $PAQUETE)'.txt'
	fi
    done
done

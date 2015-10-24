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

# Corrección de errores: comas que faltan
P[0]="(?<=\bSí\b)\s(?=\w)"	R[0]=", "
P+=("(?<=\b[Ee]s\sdecir\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Ee]n\sfin\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Pp]or\súltimo\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Oo]\ssea\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Pp]or\sconsiguiente\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Ss]in\sembargo\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Nn]o\sobstante\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Aa]demás\b)\s(?!del?\b)")	R+=(", ")
P+=("(?<=\b[Ee]n\stal\scaso\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Pp]or\slo\stanto\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Ee]n\scambio\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\b[Ee]n\sprimer\slugar\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bHola\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bGeneralmente\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bPosiblemente\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bEfectivamente\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bFinalmente\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bEn\sdefinitiva\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bPor\sregla\sgeneral\b)\s(?=\w)")	R+=(", ")
P+=("(?<=\bQuizá\b)\s(?=\w)")	R+=(", ")

P+=("(?<=\w)\s(?=\bo\sbien\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bo\ssea\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bexcepto\b)")	R+=(", ")
P+=("(?<=[b-z0-9])\s(?=\bsalvo\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bconque\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\basí\scomo\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\basí\sque\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bde\smanera\sque\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bes\sdecir\b)")	R+=(", ")
P+=("(?<=[b-z0-9])\s(?=\ba\ssaber\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpues\sbien\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bahora\sbien\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\ben\sprimer\slugar\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sotro\slado\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sun\slado\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\suna\sparte\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sotra\sparte\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\ben\sfin\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\súltimo\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bademás\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\ben\sconclusión\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\ben\stal\scaso\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bsin\sembargo\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bexcepto\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bsino\s[^a]\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bno\sobstante\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sejemplo\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bp\.\sej\.)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sel\scontrario\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sotro\slado\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\ben\scambio\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\befectivamente\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bfinalmente\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bgeneralmente\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bnaturalmente\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpor\sregla\sgeneral\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bhola\b)")	R+=(", ")
P+=("(?<=\w)\s(?=\bpero\b)")	R+=(", ")

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

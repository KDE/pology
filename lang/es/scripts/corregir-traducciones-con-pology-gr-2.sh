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

# Corrección de errores con prefijos y sufijos
P[0]="(?<=[^=.:_-]\b[Aa]nte)\-(?!(\W|[A-Z0-9]))"	R[0]=""
P+=("(?<=[^=.:_-]\b[Aa]nti)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Aa]rchi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Aa]uto)\-(?!(\W|[A-Z0-9]|configure|insert|center|key))")	R+=("")
P+=("(?<=[^=.:_-]\b[Bb]i)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Bb]ien)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Cc]o)[\s-](?!(\W|[A-Z0-9]|uk|repository|comment|module|vendortag|releasetag|id))")	R+=("")
P+=("(?<=[^=.:_-]\b[Cc]on)\-(?!(\W|[A-Z0-9]|nombre))")	R+=("")
P+=("(?<=[^=.:_-]\b[Cc]ontra)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Cc]uasi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Dd]es)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ee]pi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ee]qi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ee]x)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ee]xtra)\-(?!(\W|[A-Z0-9]|book|condensed))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ff]oto)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\bgeo)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Hh]emi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Hh][ií]per)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ii]m)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ii]n)[\s-](?!(\W|[A-Z0-9]|fraganti|situ|source|binary|advance|other|range|re\b|your|days|any|the|gst|place|most))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ii]nfra)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ii]nter)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ii]ntra)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]acro)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]axi)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]ega)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]eta)\-(?!(\W|[A-Z0-9]|language))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]icro)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]ini)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]ono)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Mm]ulti)[\s-](?!(\W|[A-Z0-9]|tab|y\b))")	R+=("")
P+=("(?<=[^=.:_-]\b[Nn]eo)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]eri)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]luri)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]oli)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]os)[\s-](?!(\W|[A-Z0-9]|[xyz]|especifica))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]ost)[\s-](?!(\W|[A-Z0-9]|and))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]re)[\s-](?!(\W|[A-Z0-9]|wrap|[yo]\spos))")	R+=("")
P+=("(?<=[^=.:_-]\b[Pp]ro)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Rr]e)[\s-](?!(\W|[A-Z0-9]|mayor|menor|bemol|sostenido))")	R+=("")
P+=("(?<=[^=.:_-]\b[Rr]etro)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]emi)[\s-](?!(\W|[A-Z0-9]|bold|condensed))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]eudo)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]im)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]in)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]obre)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]ub)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss][uú]per)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Ss]upra)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Tt]ele)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Tt]rans)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Tt]ras)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Tt]ri)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=[^=.:_-]\b[Uu]ltra)[\s-](?!(\W|[A-Z0-9]|expanded))")	R+=("")
P+=("(?<=[^=.:_-]\b[Uu]ni)[\s-](?!(\W|[A-Z0-9]|freiburg|kl))")	R+=("")
P+=("(?<=[^=.:_-]\b[Vv]ice)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
 
P+=("(?<=^[Aa]nte)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Aa]nti)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Aa]rchi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Aa]uto)\-(?!(\W|[A-Z0-9]|configure|center|insert|key))")	R+=("")
P+=("(?<=^[Bb]i)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Bb]ien)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Cc]o)[\s-](?!(\W|[A-Z0-9]|uk|repository|comment|module|vendortag|releasetag|id))")	R+=("")
P+=("(?<=^[Cc]on)\-(?!(\W|[A-Z0-9]|nombre))")	R+=("")
P+=("(?<=^[Cc]ontra)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Cc]uasi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Dd]es)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ee]pi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ee]qi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ee]x)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ee]xtra)\-(?!(\W|[A-Z0-9]|book|condensed))")	R+=("")
P+=("(?<=^[Ff]oto)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Gg]eo)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Hh]emi)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Hh][ií]per)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ii]m)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ii]n)[\s-](?!(\W|[A-Z0-9]|fraganti|situ|source|binary|advance|other|range|re\b|your|days|any|the|gst|place|most))")	R+=("")
P+=("(?<=^[Ii]nfra)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ii]nter)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ii]ntra)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]acro)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]axi)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]ega)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]eta)\-(?!(\W|[A-Z0-9]|language))")	R+=("")
P+=("(?<=^[Mm]icro)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]ini)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]ono)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Mm]ulti)[\s-](?!(\W|[A-Z0-9]|tab|y\b))")	R+=("")
P+=("(?<=^[Nn]eo)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Pp]eri)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Pp]luri)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Pp]oli)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Pp]os)[\s-](?!(\W|[A-Z0-9]|[xyz]|especifica))")	R+=("")
P+=("(?<=^[Pp]ost)[\s-](?!(\W|[A-Z0-9]|and))")	R+=("")
P+=("(?<=^[Pp]re)[\s-](?!(\W|[A-Z0-9]|wrap|[yo]\spos))")	R+=("")
P+=("(?<=^[Pp]ro)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Rr]e)[\s-](?!(\W|[A-Z0-9]|mayor|menor|bemol|sostenido))")	R+=("")
P+=("(?<=^[Rr]etro)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss]emi)[\s-](?!(\W|[A-Z0-9]|bold|condensed))")	R+=("")
P+=("(?<=^[Ss]eudo)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss]im)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss]in)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss]obre)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss]ub)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss][uú]per)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Ss]upra)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Tt]ele)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Tt]rans)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Tt]ras)\-(?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Tt]ri)[\s-](?!(\W|[A-Z0-9]))")	R+=("")
P+=("(?<=^[Uu]ltra)[\s-](?!(\W|[A-Z0-9]|expanded))")	R+=("")
P+=("(?<=^[Uu]ni)[\s-](?!(\W|[A-Z0-9]|freiburg|kl))")	R+=("")
P+=("(?<=^[Vv]ice)[\s-](?!(\W|[A-Z0-9]))")	R+=("")

P+=("\bpos(?=s\w+\b)")	R+=("post")
P+=("\bPos(?=s\w+\b)")	R+=("Post")
P+=("\bpost(?!(\W|[A-Z0-9]|[aeiours]|gre|fix|script))")	R+=("pos") 
P+=("\bPost(?!(\W|[A-Z0-9]|[aeiours]|gre|fix|script))")	R+=("Pos")

P+=("(?<=\w)\-(?=mente\b)")	R+=("")

P+=("\bmetadados\b")	R+=("metadatos")
P+=("\bMetadados\b")	R+=("Metadatos")
P+=("\binporcentaje\b")	R+=("un porcentaje")
P+=("\bincaso\b")	R+=("un caso")
P+=("\bsubmenúes\b")	R+=("submenús")
P+=("\binel\b")	R+=("en el")
P+=("\bdesesta\b")	R+=("de esta")
P+=("\bpostsible\b")	R+=("possible")
P+=("\bantialiasing\b")	R+=("suavizado de bordes")
P+=("\bAntialiasing\b")	R+=("Suavizado de bordes")
P+=("\bPresilo\b")	R+=("Pre-Silo")
P+=("\bRepag\b")	R+=("Re Pág")

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

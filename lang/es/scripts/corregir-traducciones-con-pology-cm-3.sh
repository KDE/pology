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

# Cambia artículos con género cambiado en términos técnicos.
P[0]="\bURLs\b"		R[0]="URL"
P+=("\bIRQs\b")		R+=("IRQ")

P+=("\bel(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("la")
P+=("\bEl(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("La")
P+=("\bdel(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("de la")
P+=("\bDel(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("De la")
P+=("\bun(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("una")
P+=("\bUn(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("Una")
P+=("\beste(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("esta")
P+=("\bEste(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("Esta")
P+=("\bese(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("esa")
P+=("\bEse(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("Esa")
P+=("\balgún(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("alguna")
P+=("\bAlgún(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")		R+=("Alguna")
P+=("\bningún(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")	R+=("ninguna")
P+=("\bNingún(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acro|[Ww]eb)\b)")	R+=("Ninguna")

P+=("\blos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("las")
P+=("\bLos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("Las")
P+=("\bunos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("unas")
P+=("\bUnos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("Unas")
P+=("\bestos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("estas")
P+=("\bEstos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("Estas")
P+=("\besos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("esas")
P+=("\bEsos(?=\s([Cc]achés|[Ii]nterfaces|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("Esas")
P+=("\balgunos(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("algunas")
P+=("\bAlgunos(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("Algunas")
P+=("\bningunos(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("ningunas")
P+=("\bNingunos(?=\s([Cc]aché|[Ii]nterfaz|[Ii]rq|IRQ|[Mm]acros|[Ww]ebs?)\b)")	R+=("Ningunas")

P+=("\bla(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("el")
P+=("\bLa(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("El")
P+=("\buna(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("un")
P+=("\bUna(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Un")
P+=("\besta(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("este")
P+=("\bEsta(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Este")
P+=("\besa(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("ese")
P+=("\bEsa(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Ese")
P+=("\balguna(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("algún")
P+=("\bAlguna(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("Algún")
P+=("\bninguna(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("ningún")
P+=("\bNinguna(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("Ningún")

P+=("\blas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("los")
P+=("\bLas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Los")
P+=("\bunas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("unos")
P+=("\bUnas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Unos")
P+=("\bestas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("estos")
P+=("\bEstas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Estos")
P+=("\besas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("esos")
P+=("\bEsas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Esos")
P+=("\balgunas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("algunos")
P+=("\bAlgunas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("Algunos")
P+=("\bningunas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("ningunos")
P+=("\bNingunas(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("Ningunos")

# Corrección de algunas faltas de concordancia.
P+=("(?<=[Ii]nterfaz\s)activo\b")			R+=("activa")
P+=("(?<=[Ii]nterfaz\s)cableado\b")			R+=("cableada")
P+=("(?<=[Ii]nterfaz\s)gráfico\b")			R+=("gráfica")

P+=("(?<=[Ii]nterfaces\s)activos\b")			R+=("activas")
P+=("(?<=[Ii]nterfaces\s)cableados\b")			R+=("cableadas")
P+=("(?<=[Ii]nterfaces\s)gráficos\b")			R+=("gráficas")

P+=("(?<=([Uu]rl|URL)\s)abreviada(?=s?\b)")		R+=("abreviado")
P+=("(?<=([Uu]rl|URL)\s)alternativa(?=s?\b)")		R+=("alternativo")
P+=("(?<=([Uu]rl|URL)\s)antigua(?=s?\b)")		R+=("antiguo")
P+=("(?<=([Uu]rl|URL)\s)completa(?=s?\b)")		R+=("completo")
P+=("(?<=([Uu]rl|URL)\s)configurada(?=s?\b)")		R+=("configurado")
P+=("(?<=([Uu]rl|URL)\s)correcta(?=s?\b)")		R+=("correcto")
P+=("(?<=([Uu]rl|URL)\s)dada(?=s?\b)")			R+=("dado")
P+=("(?<=([Uu]rl|URL)\s)distinta(?=s?\b)")		R+=("distinto")
P+=("(?<=([Uu]rl|URL)\s)específica(?=s?\b)")		R+=("específico")
P+=("(?<=([Uu]rl|URL)\s)estática(?=s?\b)")		R+=("estático")
P+=("(?<=([Uu]rl|URL)\s)exacta(?=s?\b)")		R+=("exacto")
P+=("(?<=([Uu]rl|URL)\s)facilitada(?=s?\b)")		R+=("facilitado")
P+=("(?<=([Uu]rl|URL)\s)incorrecta(?=s?\b)")		R+=("incorrecto")
P+=("(?<=([Uu]rl|URL)\s)introducida(?=s?\b)")		R+=("introducido")
P+=("(?<=([Uu]rl|URL)\s)mostrada(?=s?\b)")		R+=("mostrado")
P+=("(?<=([Uu]rl|URL)\s)pasada(?=s?\b)")		R+=("pasado")
P+=("(?<=([Uu]rl|URL)\s)predeterminada(?=s?\b)")	R+=("predeterminado")
P+=("(?<=([Uu]rl|URL)\s)remota(?=s?\b)")		R+=("remoto")
P+=("(?<=([Uu]rl|URL)\s)seleccionada(?=s?\b)")		R+=("seleccionado")
P+=("(?<=([Uu]rl|URL)\s)usada(?=s?\b)")			R+=("usado")
P+=("(?<=([Uu]rl|URL)\s)válida(?=s?\b)")		R+=("válido")

P+=("(?<=URL\sweb\s)válida\b")			R+=("válido")
P+=("(?<=URL\sno\s)válida\b")			R+=("válido")
P+=("(?<=URL\sno\ses\s)válida\b")		R+=("válido")
P+=("(?<=URL\ssean\s)llamadas\b")		R+=("llamados")
P+=("(?<=URL\santes\s)introducida\b")		R+=("introducido")
P+=("(?<=URL\s)a\s\la\scual\b")			R+=("al cual")
P+=("(?<=URL\s)a\s\la\sque\b")			R+=("al que")
P+=("(?<=URL\s)de\sla\s\cual\b")		R+=("del cual")
P+=("(?<=URL\s)de\sla\s\que\b")			R+=("del que")
P+=("(?<=URL\s)introducido\sno\ses\sválida\b")	R+=("introducido no es válido")

P+=("\ba\sel(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("al")
P+=("\bA\sel(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")		R+=("Al")
P+=("\bde\sel(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("del")
P+=("\bDe\sel(?=\s([Bb]ios|BIOS|[Uu]rl|URL)\b)")	R+=("Del")

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

#!/bin/bash
# 
# Corrección automática de errores en las traducciones.
# Lanza cuatro procesos en paralelo (dos ramas x dos tipos).
# Deja un registro del resultado en el subdirectorio «./Correcciones»
#
PROGRAMA=~/svnroot/pology/scripts/posieve.py
RAIZ=~/svnroot-cop
IDIOMA=es
OPCION=find-messages
PARAMETROS="-s accel:& -s case"

# Pone tildes donde debe haberlas.
P[0]="\bAun mejor\b"	R[0]="Aún mejor"
P[1]="\baun mejor\b"	R[1]="aún mejor"
P[2]="\bAun peor\b"	R[2]="Aún peor"
P[3]="\baun peor\b"	R[3]="aún peor"
P[4]="\bCasos limites?\b"	R[4]="Casos límite"
P[5]="\bcasos limites?\b"	R[5]="casos límite"
P[6]="\bEl como\b"	R[6]="El cómo"
P[7]="\bel como\b"	R[7]="el cómo"
P[8]="\bEl interprete\b"	R[8]="El intérprete"
P[9]="\bel interprete\b"	R[9]="el intérprete"
P[10]="\bEl limite\b"	R[10]="El límite"
P[11]="\bel limite\b"	R[11]="el límite"
P[12]="\bEl numero\b"	R[12]="El número"
P[13]="\bel numero\b"	R[13]="el número"
P[14]="\bEl porque\b"	R[14]="El porqué"
P[15]="\bel porque\b"	R[15]="el porqué"
P[16]="\bEl termino\b"	R[16]="El término"
P[17]="\bel termino\b"	R[17]="el término"
P[18]="\bEl titulo\b"	R[18]="El título"
P[19]="\bel titulo\b"	R[19]="el título"
P[20]="\bEl vinculo\b"	R[20]="El vínculo"
P[21]="\bel vinculo\b"	R[21]="el vínculo"
P[22]="\bFormula\b"	R[22]="Fórmula" # excepto 3ª persona de «formular»
P[23]="\bformula\b"	R[23]="fórmula"
P[24]="\bLos numeros\b"	R[24]="Los números"
P[25]="\blos numeros\b"	R[25]="los números"
P[26]="\bLos porques\b"	R[26]="Los porqués"
P[27]="\blos porques\b"	R[27]="los porqués"
P[28]="\bLos terminos\b"	R[28]="Los términos"
P[29]="\blos terminos\b"	R[29]="los términos"
P[30]="\bLos titulos\b"		R[30]="Los títulos"
P[31]="\blos titulos\b"		R[31]="los títulos"
P[32]="\bLos vinculos\b"	R[32]="Los vínculos"
P[33]="\blos vinculos\b"	R[33]="los vínculos"
P[34]="\bMas\b"		R[34]="Más" # excepto preposición (raramente usada)
P[35]="\bmas\b"		R[35]="más"
P[36]="\bPagina\b"	R[36]="Página" # excepto 3ª persona de «paginar»
P[37]="\bpagina\b"	R[37]="página"
P[38]="\bSe esta\b"		R[38]="Se está" # también posible «de esta»
P[39]="\bse esta\b"		R[39]="se está"
P[40]="\bSe este\b"	R[40]="Se esté" # también posible «de este»
P[41]="\bse este\b"	R[41]="se esté"
P[42]="\bSe numero\b"		R[42]="Se numeró"
P[43]="\bse numero\b"		R[43]="se numeró"
P[44]="\bSe vinculo\b"		R[44]="Se vinculó"
P[45]="\bse vinculo\b"		R[45]="se vinculó"
P[46]="\bSu limite\b"	R[46]="Su límite"
P[47]="\bsu limite\b"	R[47]="su límite"
P[48]="\bTenia\b"	R[48]="Tenía" # excepto parásito intestinal
P[49]="\btenia\b"	R[49]="tenía"
P[50]="\bTenias\b"	R[50]="Tenías" # excepto parásitos intestinales
P[51]="\btenias\b"	R[51]="tenías"
P[52]="\bUn dialogo\b"	R[52]="Un diálogo"
P[53]="\bun dialogo\b"	R[53]="un diálogo"
P[54]="\bUn interprete\b"	R[54]="Un intérprete"
P[55]="\bun interprete\b"	R[55]="un intérprete"
P[56]="\bUn limite\b"	R[56]="Un límite"
P[57]="\bun limite\b"	R[57]="un límite"
P[58]="\bUn numero\b"	R[58]="Un número"
P[59]="\bun numero\b"	R[59]="un número"
P[60]="\bUn porque\b"		R[60]="Un porqué"
P[61]="\bun porque\b"		R[61]="un porqué"
P[62]="\bUn termino\b"	R[62]="Un término"
P[63]="\bun termino\b"	R[63]="un término"
P[64]="\bUn titulo\b"		R[64]="Un título"
P[65]="\bun titulo\b"		R[65]="un título"
P[66]="\bUn vinculo\b"		R[66]="Un vínculo"
P[67]="\bun vinculo\b"		R[67]="un vínculo"
P[68]="\bUnos dialogos\b"	R[68]="Unos diálogos"
P[69]="\bunos dialogos\b"	R[69]="unos diálogos"
P[70]="\bUnos interpretes\b"	R[70]="Unos intérpretes"
P[71]="\bunos interpretes\b"	R[71]="unos intérprestes"
P[72]="\bUnos limites\b"	R[72]="Unos límites"
P[73]="\bunos limites\b"	R[73]="unos límites"
P[74]="\bUnos numeros\b"	R[74]="Unos números"
P[75]="\bunos numeros\b"	R[75]="unos números"
P[76]="\bUnos porques\b"	R[76]="Unos porqués"
P[77]="\bunos porques\b"	R[77]="unos porqués"
P[78]="\bUnos terminos\b"	R[78]="Unos términos"
P[79]="\bunos terminos\b"	R[79]="unos términos"
P[80]="\bUnos titulos\b"	R[80]="Unos títulos"
P[81]="\bunos titulos\b"	R[81]="unos títulos"
P[82]="\bUnos vinculos\b"	R[82]="Unos vínculos"
P[83]="\bunos vinculos\b"	R[83]="unos vínculos"
P[84]="\bValido\b"		R[84]="Válido" # excepto ayudante del rey
P[85]="\bvalido\b"		R[85]="válido"
P[86]="\bVease\b"		R[86]="Veáse"
P[87]="\bvease\b"		R[87]="veáse"
P[88]="\bVia\b"		R[88]="Vía"
P[89]="\bvia\b"		R[89]="vía"
P[90]="\bEl cuando\b"		R[90]="El cuándo"
P[91]="\bel cuando\b"		R[91]="el cuándo"
P[92]="\bEl que,\b"		R[92]="El qué,"
P[93]="\bel que,\b"		R[93]="el qué,"
P[94]="\bEl cuanto\b"		R[94]="El cuánto"
P[95]="\bel cuanto\b"		R[95]="el cuánto"
P[96]="\bEl donde\b"		R[96]="El dónde"
P[97]="\bel donde\b"		R[97]="el dónde"
#P[98]="\bForum\b"		R[98]="Fórum"
#P[99]="\bforum\b"		R[99]="fórum"
P[98]="\bIdem\b"		R[98]="Ídem"
P[99]="\bidem\b"		R[99]="ídem"
P[100]="\bMemorandum\b"		R[100]="Memorándum"
P[101]="\bmemorandum\b"		R[101]="memorándum"
P[102]="\bReferendum\b"		R[102]="Referéndum"
P[103]="\breferéndum\b"		R[103]="referéndum"

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

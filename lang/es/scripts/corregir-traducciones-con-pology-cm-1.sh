#!/bin/bash
# 
# Corrección automática de errores en las traducciones.
#
PROGRAMA=~/svnroot/pology/scripts/posieve.py
RAIZ=~/svnroot-cop
IDIOMA=es
OPCION=find-messages
PARAMETROS="-s accel:& -s case"

# Quita tildes innecesarias.
P[0]="\bGuión\b"	R[0]="Guion"
P[1]="\bguión\b"	R[1]="guion"
P[2]="\bSólo\b"		R[2]="Solo"
P[3]="\bsólo\b"		R[3]="solo"
P[4]="\bAquél\b"	R[4]="Aquel"
P[5]="\baquél\b"	R[5]="aquel"
P[6]="\bAquélla\b"	R[6]="Aquella"
P[7]="\baquélla\b"	R[7]="aquella"
P[8]="\bAquéllas\b"	R[8]="Aquellas"
P[9]="\baquéllas\b"	R[9]="aquellas"
P[10]="\bAquéllos\b"	R[10]="Aquellos"
P[11]="\baquéllos\b"	R[11]="aquellos"
P[12]="\bAsímismo\b"	R[12]="Asimismo"
P[13]="\basímismo\b"	R[13]="asimismo"
P[14]="\bAún así\b"	R[14]="Aun así"
P[15]="\baún así\b"	R[15]="aun así"
P[16]="\bAún cuando\b"	R[16]="Aun cuando"
P[17]="\baún cuando\b"	R[17]="aun cuando"
P[18]="\bBién\b"	R[18]="Bien"
P[19]="\bbién\b"	R[19]="bien"
P[20]="\bCada cúal\b"	R[20]="Cada cual"
P[21]="\bcada cúal\b"	R[21]="cada cual"
P[22]="\bCada quién\b"	R[22]="Cada quien"
P[23]="\bcada quién\b"	R[23]="cada quien"
P[24]="\bCián\b"	R[24]="Cian"
P[25]="\bcián\b"	R[25]="cian"
P[26]="\bContínuo\b"	R[26]="Continuo"
P[27]="\bcontínuo\b"	R[27]="continuo"
P[28]="\bCríar\b"	R[28]="Criar"
P[29]="\bcríar\b"	R[29]="criar"
P[30]="\bDá\b"		R[30]="Da"
P[31]="\bda\b"		R[31]="da"
P[32]="\bDí\b"		R[32]="Di"
P[33]="\bdí\b"		R[33]="di"
P[34]="\bDió\b"		R[34]="Dio"
P[35]="\bdió\b"		R[35]="dio"
P[36]="\bDiós\b"	R[36]="Dios"
P[37]="\bdiós\b"	R[37]="dios"
P[38]="\bÉsa\b"		R[38]="Esa"
P[39]="\bésa\b"		R[39]="esa"
P[40]="\bÉsas\b"	R[40]="Esas"
P[41]="\bésas\b"	R[41]="esas"
P[42]="\bÉse\b"		R[42]="Ese"
P[43]="\bése\b"		R[43]="ese"
P[44]="\bÉso\b"		R[44]="Eso"
P[45]="\béso\b"		R[45]="eso"
P[46]="\bÉsos\b"	R[46]="Esos"
P[47]="\bésos\b"	R[47]="esos"
P[48]="\bÉsta\b"	R[48]="Esta"
P[49]="\bésta\b"	R[49]="esta"
P[50]="\bÉstas\b"	R[50]="Estas"
P[51]="\béstas\b"	R[51]="estas"
P[52]="\bEstáte\b"	R[52]="Estate"
P[53]="\bestáte\b"	R[53]="estate"
P[54]="\bÉste\b"	R[54]="Este"
P[55]="\béste\b"	R[55]="este"
P[56]="\bÉsto\b"	R[56]="Esto"
P[57]="\bésto\b"	R[57]="esto"
P[58]="\bÉstos\b"	R[58]="Estos"
P[59]="\béstos\b"	R[59]="estos"
P[60]="\bFé\b"		R[60]="Fe"
P[61]="\bfé\b"		R[61]="fe"
P[62]="\bFiáis\b"	R[62]="Fiais"
P[63]="\bfiáis\b"	R[63]="fiais"
P[64]="\bFín\b"		R[64]="Fin"
P[65]="\bfín\b"		R[65]="fin"
P[66]="\bFué\b"		R[66]="Fue"
P[67]="\bfué\b"		R[67]="fue"
P[68]="\bFuí\b"		R[68]="Fui"
P[69]="\bfuí\b"		R[69]="fui"
P[70]="\bGuíar\b"	R[70]="Guiar"
P[71]="\bguíar\b"	R[71]="guiar"
P[72]="\bHáy\b"		R[72]="Hay"
P[73]="\bháy\b"		R[73]="hay"
P[74]="\bHóy\b"		R[74]="Hoy"
P[75]="\bhóy\b"		R[75]="hoy"
P[76]="\bHuí\b"		R[76]="Hui"
P[77]="\bhuí\b"		R[77]="hui"
P[78]="\bHuír\b"	R[78]="Huir"
P[79]="\bhuír\b"	R[79]="huir"
P[80]="\bIón\b"		R[80]="Ion"
P[81]="\bión\b"		R[81]="ion"
P[82]="\bMé\b"		R[82]="Me"
P[83]="\bmé\b"		R[83]="me"
P[84]="\bMés\b"		R[84]="Mes"
P[85]="\bmés\b"		R[85]="mes"
P[86]="\bMúy\b"		R[86]="Muy"
P[87]="\bmúy\b"		R[87]="muy"
P[88]="\bPán\b"		R[88]="Pan"
P[89]="\bpán\b"		R[89]="pan"
P[90]="\bPáz\b"		R[90]="Paz"
P[91]="\bpáz\b"		R[91]="paz"
P[92]="\bPié\b"		R[92]="Pie"
P[93]="\bpié\b"		R[93]="pie"
P[94]="\bRiáis\b"	R[94]="Riais"
P[95]="\briáis\b"	R[95]="riais"
P[96]="\bSéd\b"		R[96]="Sed"
P[97]="\bséd\b"		R[97]="sed"
P[98]="\bSól\b"		R[98]="Sol"
P[99]="\bsól\b"		R[99]="sol"
P[100]="\bSóla\b"	R[100]="Sola"
P[101]="\bsóla\b"	R[101]="sola"
P[102]="\bTí\b"		R[102]="Ti"
P[103]="\btí\b"		R[103]="ti"
P[104]="\bVéis\b"	R[104]="Veis"
P[105]="\bvéis\b"	R[105]="veis"
P[106]="\bVí\b"		R[106]="Vi"
P[107]="\bví\b"		R[107]="vi"
P[108]="\bVió\b"	R[108]="Vio"
P[109]="\bvió\b"	R[109]="vio"
P[110]="\bYá\b"		R[110]="Ya"
P[111]="\byá\b"		R[111]="ya"

P[112]="\bVieráis\b"		R[112]="Vierais"
P[113]="\bvieráis\b"		R[113]="vierais"
P[114]="\bVieséis\b"		R[114]="Vieseis"
P[115]="\bvieséis\b"		R[115]="vieseis"
P[116]="\bPusiéras\b"		R[116]="Pusieras"
P[117]="\bpusiéras\b"		R[117]="pusieras"
P[118]="\bPusiéses\b"		R[118]="Pusieses"
P[119]="\bpusiéses\b"		R[119]="pusiéses"
P[120]="\bJóven\b"		R[120]="Joven"
P[121]="\bjóven\b"		R[121]="joven"
P[122]="\bVolúmen\b"		R[122]="Volumen"
P[123]="\bvolúmen\b"		R[123]="volumen"
P[124]="\bResúmen\b"		R[124]="Resumen"
P[125]="\bresúmen\b"		R[125]="resumen"
P[126]="\bOrígen\b"		R[126]="Origen"
P[127]="\borígen\b"		R[127]="origen"
P[128]="\bExámen\b"		R[128]="Examen"
P[129]="\bexámen\b"		R[129]="examen"
P[130]="\bEstáte\b"		R[130]="Estate"
P[131]="\bestáte\b"		R[131]="estate"
P[132]="\bSupónlo\b"		R[132]="Suponlo"
P[133]="\bsupónlo\b"		R[133]="suponlo"
P[134]="\bDéles\b"		R[134]="Deles"
P[135]="\bdéles\b"		R[135]="deles"
P[136]="\bVé\b"		R[136]="Ve"
P[137]="\bvé\b"		R[137]="ve"
P[138]="\bDáis\b"		R[138]="Dais"
P[139]="\bdáis\b"		R[139]="dais"
P[140]="\bSóis\b"		R[140]="Sois"
P[141]="\bsois\b"		R[141]="sois"
P[142]="\bJesuíta\b"		R[142]="Jesuita"
P[143]="\bjesuíta\b"		R[143]="jesuita"
P[144]="\bGratuíto\b"		R[144]="Gratuito"
P[145]="\bgratuíto\b"		R[145]="gratuito"
P[146]="\bFortuíto\b"		R[146]="Fortuito"
P[147]="\bfortuíto\b"		R[147]="fortuito"
P[148]="\bFéliz\b"		R[148]="Feliz"
P[149]="\bféliz\b"		R[149]="feliz"
P[150]="\bCáriz\b"		R[150]="Cariz"
P[151]="\bcáriz\b"		R[151]="cariz"
P[152]="\bDéme\b"		R[152]="Deme"
P[153]="\bdéme\b"		R[153]="deme"
P[154]="\bDéle\b"		R[154]="Dele"
P[155]="\bdéle\b"		R[155]="dele"
P[156]="\bDése\b"		R[156]="Dese"
P[157]="\bdése\b"		R[157]="dese"
P[158]="\bDénos\b"		R[158]="Denos"
P[159]="\bdénos\b"		R[159]="denos"
P[160]="\bDéles\b"		R[160]="Deles"
P[161]="\bdéles\b"		R[161]="deles"

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

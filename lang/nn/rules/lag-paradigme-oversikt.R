#!/usr/bin/Rscript --vanilla
#
# Lag oversikt over kva kombinasjonar av bøyingar
# som eksisterer i Norsk ordbank.
#
# For kvar kombinasjon vel me éi føretrekt bøying,
# dersom dette gjev meining (det gjer det for eksempel
# ikkje for ord som berre har valfritt kjønn).
#
# Brukar òg ordfrekvensinformasjon frå KDE-omsettinga,
# for å få betre ordeksempel (funkar ikkje perfekt,
# men er nyttig).


# Innstillingar og filinnlesing -------------------------------------------

# Ymse pakkar for datahandsaming
library(tidyverse)

# Mappe som inneheld filene til Norsk ordbank
# og frekvensinformasjon frå KDE-omsettinga
mappe_ordbank = "~/utvikling/ordbanken"
mappe_frek = "~/utvikling/kde/trunk/l10n-support/nn/skript/frekvensoversikt"

# Les ordbankfiler og fjern unødvendige kolonnar
les_fil = function(filnamn) {
  d = read_tsv(paste0(mappe_ordbank, "/", filnamn))
  d$X1 = NULL           # Fjern kolonne med linjenummer
  d$`'NOB_2012'` = NULL # Fjern uinteressant kolonne
  d
}

# Les inn alle datafilene
d_lemma = les_fil("lemma_nn.txt")
d_fullform = les_fil("fullformsliste_nn.txt")
d_lemmaparadigme = les_fil("lemma_paradigme_nn.txt")
d_paradigme = les_fil("paradigme_boying_nn.txt")
d_frek = read_table(paste0(mappe_frek, "/", "frekvens-nn.dat"),
                    col_names=c("frek","OPPSLAG"), col_type="nc")



# Lag paradigmeoversikt ---------------------------------------------------

# Legg til bruksfrekvensinfo for kvar fullform,
# og oppsummer til slutt på lemmanivå
# (vil vera misvisande for homograf, men ikkje noko stort problem)
d_ffrek = d_fullform %>% 
  select(LEMMA_ID, OPPSLAG) %>% 
  distinct %>% # Vil ikkje telja frekvensinfo for duplikatbøyingar fleire gongar
  left_join(d_frek, by="OPPSLAG")
d_lfrek = d_ffrek %>% 
  group_by(LEMMA_ID) %>% 
  summarise(frek = sum(frek, na.rm = TRUE)) %>% 
  left_join(d_lemma)

# d_lemmaparadigme skal i utgangspunktet innehalda alle
# bøyingsparadigma til dei ulike lemmaa (gjer det ikkje heilt,
# men det er vel ein feil som skal rettast?), så me
# brukar denne for å finna paradigmekomboar

# Paradigma står i vilkårleg rekkjefølgje innanfor lemma,
# så me vil sjå vekk frå rekkjefølgja
d_lp = d_lemmaparadigme %>% 
  arrange(LEMMA_ID, PARADIGME_ID)

# Samandrag over paradigme for kvart lemma
d_psam_alle = d_lp %>% 
  group_by(LEMMA_ID) %>% 
  summarise(par_tekst = str_c(PARADIGME_ID, collapse=","),
            n_par = n())

# Sjå berre på tilfelle der me har valfridom i bøying
d_psam = d_psam_alle %>% 
  filter(n_par > 1)

# Legg til frekvensinfo og hent ut
# det mest frekvente lemmaet for
# kvar paradigmekombo
d_psam_pop = d_psam %>%
  left_join(d_lfrek) %>% 
  arrange(par_tekst, desc(frek)) %>% 
  distinct(par_tekst, .keep_all = TRUE) %>%  # Berre første/mest populære lemma
  arrange(desc(frek)) # Sorter paradigmekomboar etter frekvens



# Oppdatering og lagring av fil -------------------------------------------

# Gjer klar fil for manuell redigering
# Treng berre laga oversikt for ord
# som faktisk er brukte i omsettingane
d_utdata = d_psam_pop %>% 
  filter(frek > 0) %>% 
  select(par_tekst, LEMMA_ID, GRUNNFORM)
  
# Legg til ekstrakolonnar
# (Brukar NA i staden for "" på grunn av seinare eksport)
d_utdata$val = NA       # Paradigmet me vel for denne typen ord
d_utdata$kommentar = NA # Kommentar til valet/paradigmekomboen


# Les inn gammal fil (for oppdatering)
d_gammal = read_csv("paradigme-komboar.csv",
										col_types = cols(par_tekst = col_character(),
																		 LEMMA_ID = col_integer(),
																		 GRUNNFORM = col_character(),
																		 val = col_character(),
																		 kommentar = col_character()
))
d_nye = d_utdata %>% 
	anti_join(d_gammal, by = "par_tekst")
d_oppdatert = bind_rows(d_gammal, d_nye)


# Lagra oversiktsfil i CSV-format for manuell redigering
#
# Gjer det nøyaktig slik (og brukar for eksempel ikkje write_csv())
# for at fila skal kunna redigerast med LibreOffice Calc utan at
# det vert gjort formateringsendringar. Bruk følgjande innstillingar
# ved import:
#
#   Skild med: Komma (ingenting anna)
#   Formater sitatfelt som tekst: ja (kryssa av)
#
# Må etter import merkja heile «val»-kolonnen og endra «Talformat» til
# «Tekst», for å hindra at talkodar som begynner med 0 mistar 0-talet.
# (Det er *ikkje* nok eller nødvendig å gjera dette ved sjølve importen.)
#
write.csv(d_oppdatert, "paradigme-komboar.csv", row.names = FALSE, na = "")

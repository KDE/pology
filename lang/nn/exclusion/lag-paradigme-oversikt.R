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
les_fil = function(filnamn, ...) {
  d = read_tsv(paste0(mappe_ordbank, "/", filnamn), ...)
  d
}

# Les inn alle datafilene
d_lemma = les_fil(
  "lemma_nn.txt",
  col_types = cols_only(LEMMA_ID = col_integer(), GRUNNFORM = col_character()))
d_fullform = les_fil(
  "fullformsliste_nn.txt",
  col_types = cols_only(
    LEMMA_ID = col_integer(),
    OPPSLAG = col_character(),
    TAG = col_character(),
    PARADIGME_ID = col_character(),
    BOY_NUMMER = col_integer(),
    FRADATO = col_character(),
    TILDATO = col_character(),
    NORMERING = col_character()
  )
)
d_lemmaparadigme = les_fil(
  "lemma_paradigme_nn.txt",
  col_types = cols_only(
    LEMMA_ID = col_integer(),
    PARADIGME_ID = col_character(),
    NORMERING = col_character(),
    FRADATO = col_character(),
    TILDATO = col_character(),
    KOMMENTAR = col_character()
  )
)
d_paradigme = les_fil(
  "paradigme_boying_nn.txt",
  col_types = cols_only(
    PARADIGME_ID = col_character(),
    BOY_NUMMER = col_integer(),
    BOY_GRUPPE = col_character(),
    BOY_UTTRYKK = col_character()
  )
)
d_frek = read_table(paste0(mappe_frek, "/", "frekvens-nn.dat"),
                    col_names = c("frek", "OPPSLAG"), col_types = "nc")



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
  summarise(frek = sum(frek, na.rm = TRUE), .groups = "drop") %>% 
  left_join(d_lemma, by = "LEMMA_ID")

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
            n_par = n(), .groups = "drop")

# Sjå berre på tilfelle der me har valfridom i bøying
d_psam = d_psam_alle %>% 
  filter(n_par > 1)

# Legg til frekvensinfo og hent ut
# det mest frekvente lemmaet for
# kvar paradigmekombo
d_psam_pop = d_psam %>%
  left_join(d_lfrek, by = "LEMMA_ID") %>% 
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
d_utdata$val = NA_character_       # Paradigmet me vel for denne typen ord
d_utdata$kommentar = NA_character_ # Kommentar til valet/paradigmekomboen
d_utdata$unntak = NA_character_    # Ev. unntak, på forma LEMMA_ID1=700,LEMMA_ID2=49G,…


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




# Lag ordekskluderingsfil -------------------------------------------------

# Skal så laga ei oversikt over alle orda som skal ekskluderast
d = d_oppdatert

# Bør først sjekka at paradigmekoden me har valt faktisk er
# ein av dei gyldige paradigmekodane for lemmaet
d = d %>% mutate(ok_val = is.na(val) | 
								 	str_detect(par_tekst, str_c("\\b", d$val, "\\b")))
if(!all(d$ok_val)) {
	stop(paste0("Minst éin paradigmekombo har ugyldig paradigmekode valt:\n",
							paste0(format(filter(d, !ok_val)), collapse="\n")))
}

# Unntak er litt komlisert å handtera,
# men det går bra … :)

# Hent ut unntaka frå ein tekststreng
# og lag ein tibble med tilhøyrande info
hent_unntak = function(x) {
  str_split_fixed(x, "=", 2) %>% 
	as_tibble %>% 
	set_names(c("LEMMA_ID", "val"))
}

# Unntaksmønstera, med éi rad for
# kvart lemma som har eit unntak
d_unntaksmønster = d %>% 
	filter(!is.na(unntak)) %>% 
	select(par_tekst, unntak) %>%
	mutate(
		unntak_liste =
		  str_split(unntak, ",") %>%
		  map(hent_unntak)) %>% 
	unnest(unntak_liste) %>% 
	mutate(LEMMA_ID = as.integer(LEMMA_ID))

# Sjekk at me ikkje har fleire unntak for same lemma
stopifnot(!any(duplicated(d_unntaksmønster)))

# Sjekk at alle unntaka viser til LEMMA_ID-ar som
# finst og at tilhøyrande PARADIGME_ID-ar òg finst
# for den aktuelle LEMMA_ID-en
unntak_feil = d_unntaksmønster %>% 
	anti_join(d_fullform, by=c("LEMMA_ID", "val"="PARADIGME_ID"))
if(nrow(unntak_feil) > 0) {
	stop(paste0("Minst eitt unntak viser til ugyldig lemma-ID eller paradigme-ID:\n",
							paste0(format(unntak_feil), collapse="\n")))
}


# Alle fullformene + info om føretrekt paradigme
# for lemmaa som følgjer hovudregelen
d_alle_hovudregel = d_oppdatert %>% 
	select(par_tekst, val) %>% 
	left_join(d_psam, by="par_tekst") %>% 
	right_join(d_fullform, by="LEMMA_ID")

# Alle fullformene for unntaka + info om føretrekt paradigme
d_unntak = d_unntaksmønster %>% 
	left_join(d_fullform, by="LEMMA_ID")

# Alle fullformene, med unntak der det trengst +
# info om føretrekt paradigme
d_alle = d_alle_hovudregel %>% 
	anti_join(d_unntak, by="LEMMA_ID") %>% 
	bind_rows(d_unntak)

# Info om ei fullform er gyldig
d_alle = d_alle %>% 
	mutate(gyldig_form = (is.na(val) | PARADIGME_ID == val))
	
# Fullformene som er gyldige eller ugyldige
d_gyldige = d_alle %>% filter(gyldig_form)
d_ugyldige = d_alle %>% filter(!gyldig_form)

# Men at ei form er ugyldig er ikkje god nok
# grunn til å ekskludera ho. Det kan vera det
# same «ordet» òg er med blant dei gyldige
# formene, anten i det utvaldet paradigmet til
# lemmaet, eller for eit anna lemma (homografar).
# Eksluderer derfor berre dei orda som ikkje
# finst i samlinga av gyldige ord.
ord_ekskluder = sort(setdiff(d_ugyldige$OPPSLAG, d_gyldige$OPPSLAG))

# Lagra ekskluderingsordlista
write_lines(ord_ekskluder, "feil-paradigme.dat")

# Vis orda me *har* brukt i omsettingane men
# som no vert ekskluderte …
cat("Ord brukte i omsetjingane som no vert forbodne:")
d_frek %>% 
	filter(OPPSLAG %in% ord_ekskluder) %>% 
	print(n=Inf)

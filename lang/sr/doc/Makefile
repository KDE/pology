# -*- Makefile -*-
ALL_SOURCES:=$(wildcard *.docbook)
ALL_TARGETS:=$(patsubst %.docbook,%.html,$(ALL_SOURCES))

all: $(ALL_TARGETS)

%.html: %.docbook
	xmllint --valid $< >/dev/null
	./subs-svn-data.sh $<
	xsltproc local.xsl $<.tmp >$@
	rm $<.tmp
	tidy -q --show-warnings no -utf8 -w 0 -m $@; test -z
	# Remove title= attributes to sectioning classes,
	# because they cause a tooltip to be shown wherever the pointer is.
	perl -pi -e 's/(<div[^>]*?class="(abstract|article|book|chapter|sect)[^>]*?) *title=".*?"/\1/' $@

clean:
	rm -f *.html *~


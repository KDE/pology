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

clean:
	rm -f *.html *~


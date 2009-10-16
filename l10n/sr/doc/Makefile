# -*- Makefile -*-
ALL_SOURCES:=$(wildcard *.docbook)
ALL_TARGETS:=$(patsubst %.docbook,%.html,$(ALL_SOURCES))

all: $(ALL_TARGETS)

%.html: %.docbook
	xmllint --valid $< >/dev/null
	bldate=`date "+%-d. %B %Y."`
	#vcsdate=`svn info --xml $< | grep '<text-updated>' | sed 's/^[^>]*>\([^T]*\).*/\1/'`
	#vcsrev=`svn info --xml $< | grep revision= | tail -1 | sed 's/^.*"\([^"]*\)".*/\1/'`
	sed -e "s/@bldate@/$$bldate/" -e "s/@vcsdate@/$$vcsdate/" -e "s/@vcsrev@/$$vcsrev/" < $< > $<.tmp
	xsltproc local.xsl $<.tmp >$@
	rm $<.tmp
	tidy -q --show-warnings no -utf8 -w 0 -m $@; test -z

clean:
	rm -f *.html *~


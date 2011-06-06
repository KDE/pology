<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<xsl:import href="/usr/share/xml/docbook/stylesheet/docbook-xsl/html/chunk.xsl"/>
<xsl:import href="docbook-html-common.xsl"/>

<xsl:param name="base.dir">html/</xsl:param>
<xsl:param name="chunker.output.encoding">UTF-8</xsl:param>

<!-- Chunk on the level of chapters. -->
<xsl:param name="chunk.section.depth" select="0"/>

<!-- Do not output chunking progress. -->
<xsl:param name="chunk.quietly" select="1"/>

<!-- Use section IDs for chunked HTML file names. -->
<xsl:param name="use.id.as.filename" select="1"/>

</xsl:stylesheet>

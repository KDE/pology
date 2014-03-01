<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0">

<!-- Make each generated HTML page include the style sheet file. -->
<xsl:param name="html.stylesheet.type">text/css</xsl:param>
<xsl:param name="html.stylesheet" select="'style.css'"/>

<!-- Format sections as "X.Y.Z. Title". -->
<xsl:param name="section.autolabel" select="1"/>
<xsl:param name="section.label.includes.component.label" select="1"/>

<!-- Let there be only the top TOC. -->
<xsl:param name="generate.toc" select="'book toc'"/>

<!-- Override <programlisting> to include language info comment. -->
<xsl:template match="programlisting">
    <xsl:variable name="id">
        <xsl:call-template name="object.id"/>
    </xsl:variable>
    <xsl:call-template name="anchor"/>
    <pre>
        <xsl:apply-templates select="." mode="common.html.attributes"/>
        <xsl:if test="@language != ''">
            <xsl:comment>language: <xsl:value-of select="@language"/></xsl:comment>
        </xsl:if>
        <xsl:apply-templates/>
    </pre>
</xsl:template>

<xsl:output method="html" encoding="UTF-8" indent="no"/>

</xsl:stylesheet>

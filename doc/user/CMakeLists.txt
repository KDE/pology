if(NOT CAN_BUILD_DOCBOOK)
    return()
endif()

if(CAN_HIGHLIGHT)
    set(highlight HIGHLIGHT)
endif()

set(docs
    top.docbook # master must be first
    about.docbook
    ascription.docbook
    combined.docbook
    common.docbook
    diffpatch.docbook
    lingo.docbook
    misctools.docbook
    poformat.docbook
    programming.docbook
    sieving.docbook
    stdopt-colors.docbook
    stdopt-filesfrom.docbook
    stdopt-incexc.docbook
    stdopt-wrapping.docbook
    summit.docbook
)
set(images
)

set(lang "en_US")
get_current_source_subdir(doctype -1 -1)

docbook_book_to_html_chunked(
    DOCS ${docs} EXTRAS ${images}
    CSSFILE ${CMAKE_SOURCE_DIR}/util/docbook-html-style.css
    XSLFILE ${CMAKE_BINARY_DIR}/util/docbook-html-chapters.xsl
    OUTDIR html
    DESTINATION ${DOC_INSTALL_DIR}/${doctype}
    RENAME ${lang}
    RENAMECSS style.css
    ${highlight}
)

docbook_book_to_html_single(
    DOCS ${docs} EXTRAS ${images}
    CSSFILE ${CMAKE_SOURCE_DIR}/util/docbook-html-style.css
    XSLFILE ${CMAKE_BINARY_DIR}/util/docbook-html-mono.xsl
    OUTFILE index-mono.html PIPEOUT
    DESTINATION ${DOC_INSTALL_DIR}/${doctype}/${lang}
    RENAME index-mono.html
    RENAMECSS style.css
    ${highlight}
)

if(NOT CAN_BUILD_DOCBOOK)
    return()
endif()

set(docs
    top.docbook # master must be first
    trapnakron.docbook
)
set(images
    google-query-trapnakron-o2t.png
    google-query-trapnakron-t2o.png
    kate-syntax-synder.png
)

get_current_source_subdir(lang -2 -2)
set(doctype "lang/${lang}")

docbook_book_to_html_chunked(
    DOCS ${docs} EXTRAS ${images}
    CSSFILE ${CMAKE_SOURCE_DIR}/util/docbook-html-style.css
    XSLFILE ${CMAKE_SOURCE_DIR}/util/docbook-html-chapters.xsl
    OUTDIR html
    DESTINATION ${DOC_INSTALL_DIR}/${doctype}
    RENAME ${lang}
    RENAMECSS style.css
)

docbook_book_to_html_single(
    DOCS ${docs} EXTRAS ${images}
    CSSFILE ${CMAKE_SOURCE_DIR}/util/docbook-html-style.css
    XSLFILE ${CMAKE_SOURCE_DIR}/util/docbook-html-mono.xsl
    OUTFILE index-mono.html PIPEOUT
    DESTINATION ${DOC_INSTALL_DIR}/${doctype}/${lang}
    RENAME index-mono.html
    RENAMECSS style.css
)

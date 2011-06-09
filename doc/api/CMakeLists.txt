if(NOT CAN_BUILD_EPYDOC)
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

set(lang "en_US")
get_current_source_subdir(doctype -1 -1)

epydoc_to_html(
    PYPKGDIR ${CMAKE_SOURCE_DIR}/pology
    OUTDIR ${lang}
    EPYOPTS --no-sourcecode --no-frames --no-private
            --exclude=external --exclude=internal
    DESTINATION ${DOC_INSTALL_DIR}/${doctype}
)

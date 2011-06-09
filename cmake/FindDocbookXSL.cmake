# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

# Find root directory of XSL stylesheets.
if(NOT DOCBOOK_XSL_DIR)
    message(STATUS
        "Looking for Docbook XSL stylesheets "
        "(use -DDOCBOOK_XSL_DIR= to set manually)...")
    set(docbook_stylesheet_paths
        share/xml/docbook/stylesheet/docbook-xsl
        share/xml/docbook/xsl-stylesheets
        share/sgml/docbook/xsl-stylesheets
        share/xml/docbook/stylesheet/nwalsh/current
        share/xml/docbook/stylesheet/nwalsh
        share/xsl/docbook
        share/xsl/docbook-xsl
    )
    find_path(DOCBOOK_XSL_DIR lib/lib.xsl
        PATHS ${CMAKE_SYSTEM_PREFIX_PATH}
        PATH_SUFFIXES ${docbook_stylesheet_paths}
    )
else()
    if(NOT EXISTS ${DOCBOOK_XSL_DIR}/lib/lib.xsl)
        set(DOCBOOK_XSL_DIR no)
    endif()
endif()

# Check stylesheets version.
if(EXISTS ${DOCBOOK_XSL_DIR}/VERSION)
    file(READ ${DOCBOOK_XSL_DIR}/VERSION contents)
    string(REGEX REPLACE ".*<fm:Version>([^<]*)</fm:Version>.*" "\\1"
                         rawversion "${contents}")
    string(REGEX REPLACE "(.*[0-9]).*" "\\1"
                         DOCBOOK_XSL_VERSION "${rawversion}")
endif()

find_package_handle_standard_args(DocbookXSL
    REQUIRED_VARS DOCBOOK_XSL_DIR
    VERSION_VAR DOCBOOK_XSL_VERSION
)

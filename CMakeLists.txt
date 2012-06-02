cmake_minimum_required(VERSION 2.8.3)

###
### Set project.
###

set(CMAKE_MODULE_PATH ${CMAKE_CURRENT_SOURCE_DIR}/cmake ${CMAKE_MODULE_PATH})

set(PROJECT_NAME "pology")
file(READ "VERSION" version)
string(REPLACE "\n" "" version "${version}")
set(PROJECT_VERSION "${version}")
message(STATUS "Configuring ${PROJECT_NAME} ${PROJECT_VERSION}")
project(${PROJECT_NAME} NONE)

if(NOT cmake_install_prefix_cached)
    if(CMAKE_INSTALL_PREFIX_INITIALIZED_TO_DEFAULT)
        message(STATUS
            "Installation prefix: ${CMAKE_INSTALL_PREFIX} "
            "(use -DCMAKE_INSTALL_PREFIX= to set manually)")
    else()
        message(STATUS "Installation prefix: ${CMAKE_INSTALL_PREFIX}")
    endif()
endif()
set(cmake_install_prefix_cached ${CMAKE_INSTALL_PREFIX}
    CACHE INTERNAL "Cache stamp for CMAKE_INSTALL_PREFIX.")

find_package(Python2 2.5 REQUIRED)
find_package(DocbookXSL 1.75.2)
find_package(LibXml2)
find_package(Xsltproc)
find_package(Epydoc 3.0)
find_package(Msgfmt 0.17)
find_package(Msgmerge 0.17)

if(DOCBOOKXSL_FOUND AND LIBXML2_FOUND AND XSLTPROC_FOUND)
    set(CAN_BUILD_DOCBOOK yes)
    # Configure paths in style sheet extensions.
    set(CONFIG_DBXSLDIR ${DOCBOOK_XSL_DIR})
    file(GLOB_RECURSE xslfiles RELATIVE ${CMAKE_SOURCE_DIR} "util/*.xsl")
    foreach(xslfile ${xslfiles})
        configure_file(${CMAKE_SOURCE_DIR}/${xslfile}
                       ${CMAKE_BINARY_DIR}/${xslfile} @ONLY)
    endforeach()
else()
    set(CAN_BUILD_DOCBOOK no)
endif()

if(EPYDOC_FOUND)
    set(CAN_BUILD_EPYDOC yes)
else()
    set(CAN_BUILD_EPYDOC no)
endif()

if(MSGFMT_FOUND AND MSGMERGE_FOUND)
    set(CAN_BUILD_PO yes)
else()
    set(CAN_BUILD_PO no)
endif()

# Pology is needed to build itself, bootstrap it.
set(ENV{PYTHON_PATH} "${CMAKE_SOURCE_DIR}:$ENV{PYTHON_PATH}")
set(POLOGY_LIB_DIR "${CMAKE_SOURCE_DIR}/pology")

# Set general installation paths.
set(BIN_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/bin)
set(DATA_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/share/${PROJECT_NAME})
set(DOC_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/share/doc/${PROJECT_NAME})
set(MO_INSTALL_DIR ${CMAKE_INSTALL_PREFIX}/share/locale)

# Include modules used by many subdirectories.
include(DocbookTools)
include(EpydocTools)
include(GettextTools)
include(PologyTools)
include(ProjectTools)
include(Python2Tools)

# Include subdirectories.
add_subdirectory(pology)
add_subdirectory(scripts)
add_subdirectory(sieve)
add_subdirectory(lang)
add_subdirectory(doc)
add_subdirectory(spec)
add_subdirectory(completion)
add_subdirectory(syntax)
add_subdirectory(po)

# Report build problems.

if(NOT CAN_BUILD_DOCBOOK)
    set(msg "WARNING:
    Docbook documentation (e.g. the Pology user manual) will not be built
    because the following dependencies are missing or too old:")
    if(NOT DOCBOOKXSL_FOUND)
        set(msg "${msg}
    - Docbook XSL stylesheets
        home page: http://wiki.docbook.org/DocBookXslStylesheets,
        possible package names: docbook-xsl")
    endif()
    if(NOT LIBXML2_FOUND)
        set(msg "${msg}
    - xmllint, XML validator
        home page: http://xmlsoft.org/
        possible package names: libxml2-utils")
    endif()
    if(NOT XSLTPROC_FOUND)
        set(msg "${msg}
    - xsltproc, XSLT processor
        home page: http://xmlsoft.org
        possible package names: xsltproc")
    endif()
    message(STATUS "${msg}")
endif()

if(NOT CAN_BUILD_EPYDOC)
    set(msg "WARNING:
    API documentation for the Pology Python library will not be built
    because the following dependencies are missing or too old:")
    if(NOT EPYDOC_FOUND)
        set(msg "${msg}
    - Epydoc, Python doctring to HTML doc generator
        home page: http://epydoc.sourceforge.net
        possible package names: python-epydoc, epydoc")
    endif()
    message(STATUS "${msg}")
endif()

if(NOT CAN_BUILD_PO)
    set(msg "WARNING:
    Translations of Pology user interface and documentation will not be built
    because the following dependencies are missing or too old:")
    if(NOT MSGFMT_FOUND OR NOT MSGMERGE_FOUND)
        set(msg "${msg}
    - Gettext tools
        home page: http://www.gnu.org/software/gettext/
        possible package names: gettext")
    endif()
    message(STATUS "${msg}")
endif()


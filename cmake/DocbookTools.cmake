# TODO: Add doc comments for all this stuff.

if(NOT LIBXML2_XMLLINT_EXECUTABLE)
    find_package(LibXml2)
endif()
if(NOT XSLTPROC_EXECUTABLE)
    find_package(Xsltproc)
endif()

if(NOT dbt_target_count)
    set(dbt_target_count 1)
endif()

# Sed search and replace expression to
# remove title= attributes to sectioning classes on HTML pages,
# because they cause a tooltip to be shown wherever the pointer is.
set(sedrepl_notitle
    "'s/(<div[^>]* class=\"(abstract|article|book|chapter|sect)[^>]*) title=\"[^\"]*\"/\\1/g'")


function(GET_ABSOLUTE_PATHS abspathsvar absroot)
    set(paths ${ARGN})

    set(abspaths)
    foreach(path ${paths})
        if(NOT IS_ABSOLUTE ${path})
            set(path ${absroot}/${path})
        endif()
        set(abspaths ${abspaths} ${path})
    endforeach()

    set(${abspathsvar} ${abspaths} PARENT_SCOPE)

endfunction()


macro(DOCBOOK_BOOK_TO_HTML_CHUNKED)

    set(optargs)
    set(svalargs TARGET CSSFILE XSLFILE OUTDIR DESTINATION RENAME RENAMECSS)
    set(mvalargs DOCS EXTRAS)
    cmake_parse_arguments(DBT_BHC
                          "${optargs}" "${svalargs}" "${mvalargs}" ${ARGN})
    if(DBT_BHC_UNPARSED_ARGUMENTS)
        string(REPLACE ";" " " badargs "${DBT_BHC_UNPARSED_ARGUMENTS}")
        message(FATAL_ERROR "Unknown arguments: ${badargs}")
    endif()
    list(LENGTH DBT_BHC_DOCS ndocs)
    if(ndocs LESS 1)
        message(FATAL_ERROR "No Docbook files set (DOCS).")
    endif()
    if(NOT DBT_BHC_XSLFILE)
        message(FATAL_ERROR "XSL file not set (XSLFILE).")
    endif()
    if(NOT DBT_BHC_OUTDIR)
        message(FATAL_ERROR "Output directory for chunks not set (OUTDIR).")
    endif()
    if(NOT DBT_BHC_DESTINATION)
        message(FATAL_ERROR "Install directory not set (DESTINATION).")
    endif()
    if(NOT DBT_BHC_RENAME)
        set(DBT_BHC_RENAME ${DBT_BHC_OUTDIR})
    endif()

    get_absolute_paths(docfiles ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_DOCS})
    get_absolute_paths(extrafiles ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_EXTRAS})
    get_absolute_paths(xslfile ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_XSLFILE})
    get_absolute_paths(cssfile ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_CSSFILE})
    get_absolute_paths(outdir ${CMAKE_CURRENT_BINARY_DIR} ${DBT_BHC_OUTDIR})
    get_absolute_paths(rnmdir ${CMAKE_CURRENT_BINARY_DIR} ${DBT_BHC_RENAME})

    if(NOT DBT_BHC_TARGET)
        string(REPLACE ${CMAKE_SOURCE_DIR}/ "" srcsubdir
                       ${CMAKE_CURRENT_SOURCE_DIR})
        string(REPLACE "/" "-" targbase ${srcsubdir})
        set(target "${targbase}-dbt${dbt_target_count}-book-to-html-chunked")
        math(EXPR dbt_target_count "${dbt_target_count} + 1")
    else()
        set(target ${DBT_BHC_TARGET})
    endif()

    list(GET docfiles 0 mdocfile)
    set(targfilebase ${target}-buildstamp)
    set(targfile ${rnmdir}/${targfilebase})
    add_custom_command(
        OUTPUT ${targfile}
        COMMAND rm -rf ${rnmdir}
        COMMAND ${LIBXML2_XMLLINT_EXECUTABLE} --noout --xinclude --postvalid
                ${mdocfile}
        COMMAND ${XSLTPROC_EXECUTABLE} --xinclude -o ${outdir}
                ${xslfile} ${mdocfile}
        COMMAND mv ${outdir} ${outdir}-tmp
        COMMAND mv ${outdir}-tmp ${rnmdir}
        COMMAND sed -i -r ${sedrepl_notitle} ${rnmdir}/*.html
        COMMAND touch ${targfile}
        DEPENDS ${docfiles} ${xslfile}
    )
    add_custom_target(${target} ALL DEPENDS ${targfile})
    install(DIRECTORY ${rnmdir} DESTINATION ${DBT_BHC_DESTINATION}
            PATTERN ${targfilebase} EXCLUDE)
    install(FILES ${extrafiles}
            DESTINATION ${DBT_BHC_DESTINATION}/${DBT_BHC_RENAME})
    install(FILES ${cssfile}
            DESTINATION ${DBT_BHC_DESTINATION}/${DBT_BHC_RENAME}
            RENAME ${DBT_BHC_RENAMECSS})

endmacro()


macro(DOCBOOK_BOOK_TO_HTML_SINGLE)

    set(optargs PIPEOUT)
    set(svalargs TARGET CSSFILE XSLFILE OUTFILE DESTINATION RENAME RENAMECSS)
    set(mvalargs DOCS EXTRAS)
    cmake_parse_arguments(DBT_BHC
                          "${optargs}" "${svalargs}" "${mvalargs}" ${ARGN})
    if(DBT_BHC_UNPARSED_ARGUMENTS)
        string(REPLACE ";" " " badargs "${DBT_BHC_UNPARSED_ARGUMENTS}")
        message(FATAL_ERROR "Unknown arguments: ${badargs}")
    endif()
    list(LENGTH DBT_BHC_DOCS ndocs)
    if(ndocs LESS 1)
        message(FATAL_ERROR "No Docbook files set (DOCS).")
    endif()
    if(NOT DBT_BHC_XSLFILE)
        message(FATAL_ERROR "XSL file not set (XSLFILE).")
    endif()
    if(NOT DBT_BHC_OUTFILE)
        message(FATAL_ERROR "Output file not set (OUTFILE).")
    endif()
    if(NOT DBT_BHC_DESTINATION)
        message(FATAL_ERROR "Install directory not set (DESTINATION).")
    endif()
    if(NOT DBT_BHC_RENAME)
        set(DBT_BHC_RENAME ${DBT_BHC_OUTFILE})
    endif()

    get_absolute_paths(docfiles ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_DOCS})
    get_absolute_paths(extrafiles ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_EXTRAS})
    get_absolute_paths(xslfile ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_XSLFILE})
    get_absolute_paths(cssfile ${CMAKE_CURRENT_SOURCE_DIR} ${DBT_BHC_CSSFILE})
    get_absolute_paths(outfile ${CMAKE_CURRENT_BINARY_DIR} ${DBT_BHC_OUTFILE})

    if(NOT DBT_BHC_TARGET)
        string(REPLACE ${CMAKE_SOURCE_DIR}/ "" srcsubdir
                       ${CMAKE_CURRENT_SOURCE_DIR})
        string(REPLACE "/" "-" targbase ${srcsubdir})
        set(target "${targbase}-dbt${dbt_target_count}-book-to-html-chunked")
        math(EXPR dbt_target_count "${dbt_target_count} + 1")
    else()
        set(target ${DBT_BHC_TARGET})
    endif()
    if(DBT_BHC_PIPEOUT)
        set(pipeopt "-o" ${outfile})
    endif()

    list(GET docfiles 0 mdocfile)
    add_custom_command(
        OUTPUT ${outfile}
        COMMAND rm -rf ${outfile}
        COMMAND ${LIBXML2_XMLLINT_EXECUTABLE} --noout --xinclude --postvalid
                ${mdocfile}
        COMMAND ${XSLTPROC_EXECUTABLE} --xinclude ${pipeopt}
                ${xslfile} ${mdocfile}
        COMMAND sed -i -r ${sedrepl_notitle} ${rnmdir}/*.html
        DEPENDS ${docfiles} ${xslfile}
    )
    add_custom_target(${target} ALL DEPENDS ${outfile})
    install(FILES ${outfile} DESTINATION ${DBT_BHC_DESTINATION}
            RENAME ${DBT_BHC_RENAME})
    install(FILES ${extrafiles} DESTINATION ${DBT_BHC_DESTINATION})
    install(FILES ${cssfile} DESTINATION ${DBT_BHC_DESTINATION}
            RENAME ${DBT_BHC_RENAMECSS})

endmacro()

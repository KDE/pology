# TODO: Add doc comments for all this stuff.

if(NOT EPYDOC_EXECUTABLE)
    find_package(Epydoc 3.0)
endif()

if(NOT epyt_target_count)
    set(epyt_target_count 1)
endif()


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


macro(EPYDOC_TO_HTML)

    set(optargs)
    set(svalargs PYPKGDIR OUTDIR DESTINATION TARGET)
    set(mvalargs EPYOPTS)
    cmake_parse_arguments(EPYT_H
                          "${optargs}" "${svalargs}" "${mvalargs}" ${ARGN})
    if(EPYT_H_UNPARSED_ARGUMENTS)
        string(REPLACE ";" " " badargs "${EPYT_H_UNPARSED_ARGUMENTS}")
        message(FATAL_ERROR "Unknown arguments: ${badargs}")
    endif()
    if(NOT EPYT_H_OUTDIR)
        message(FATAL_ERROR "Output directory for HTML pages not set (OUTDIR).")
    endif()
    if(NOT EPYT_H_DESTINATION)
        message(FATAL_ERROR "Install directory not set (DESTINATION).")
    endif()

    get_absolute_paths(pypkgdir ${CMAKE_CURRENT_SOURCE_DIR} ${EPYT_H_PYPKGDIR})
    get_absolute_paths(outdir ${CMAKE_CURRENT_BINARY_DIR} ${EPYT_H_OUTDIR})

    if(NOT EPYT_H_TARGET)
        string(REPLACE ${CMAKE_SOURCE_DIR}/ "" srcsubdir
                       ${CMAKE_CURRENT_SOURCE_DIR})
        string(REPLACE "/" "-" targbase ${srcsubdir})
        set(target "${targbase}-epyt${epyt_target_count}-epydoc-to-html")
        math(EXPR epyt_target_count "${epyt_target_count} + 1")
    else()
        set(target ${EPYT_H_TARGET})
    endif()

    file(GLOB_RECURSE pyfiles "${pypkgdir}/*.py") # evil
    set(targfilebase ${target}-buildstamp)
    set(targfile ${outdir}/${targfilebase})
    add_custom_command(
        OUTPUT ${targfile}
        COMMAND test x == `find ${pypkgdir} -iname *.pyc -print0`x
                || (echo 'There are some .pyc files in ${pypkgdir},'
                         'you must remove them.'
                    && exit 1)
        COMMAND rm -rf ${outdir} && mkdir -p ${outdir}
        COMMAND PYTHONDONTWRITEBYTECODE=1 # do not pollute srcdir with *.pyc files
                ${EPYDOC_EXECUTABLE} ${pypkgdir}/ -o ${outdir}
                ${EPYT_H_EPYOPTS}
        COMMAND touch ${targfile}
        DEPENDS ${pyfiles}
    )
    add_custom_target(${target} ALL DEPENDS ${targfile})
    install(DIRECTORY ${outdir} DESTINATION ${EPYT_H_DESTINATION}
            PATTERN ${targfilebase} EXCLUDE)

endmacro()



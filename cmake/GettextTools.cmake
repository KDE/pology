# TODO: Add doc comments for all this stuff.

if(NOT MSGFMT_EXECUTABLE)
    find_package(Msgfmt)
endif()
if(NOT MSGMERGE_EXECUTABLE)
    find_package(Msgmerge)
endif()

if(NOT gtxt_target_count)
    set(gtxt_target_count 1)
endif()


macro(INSTALL_PO_DOMAIN podomain linguas localedir)

    if(NOT MSGFMT_EXECUTABLE)
        message(FATAL_ERROR "MSGFMT_EXECUTABLE is not set.")
    endif()

    set(alinguas ${linguas})
    if(NOT IS_ABSOLUTE ${linguas})
        set(alinguas ${CMAKE_CURRENT_SOURCE_DIR}/${linguas})
    endif()
    if(NOT EXISTS ${alinguas})
        message(FATAL_ERROR
            "The language list file '${alinguas}' is missing.")
    endif()
    file(READ ${alinguas} fc)
    string(REGEX REPLACE "#[^\n]*\n" " " fc ${fc})
    string(REGEX MATCHALL "[^ \t\n]+" langs ${fc})

    string(REPLACE ${CMAKE_SOURCE_DIR}/ "" srcsubdir
                   ${CMAKE_CURRENT_SOURCE_DIR})
    string(REPLACE "/" "-" targbase ${srcsubdir})
    set(target "${targbase}-gtxt${gtxt_target_count}-install-po-domain")
    math(EXPR gtxt_target_count "${gtxt_target_count} + 1")

    set(mofiles)
    foreach(lang ${langs})
        set(pofile ${CMAKE_CURRENT_SOURCE_DIR}/${lang}.po)
        if(NOT EXISTS ${pofile})
            message(FATAL_ERROR
                "The PO file '${pofile}' expected according to '${alinguas}' "
                "is missing.")
        endif()
        set(mofile ${CMAKE_CURRENT_BINARY_DIR}/${lang}.mo)
        add_custom_command(
            OUTPUT ${mofile}
            COMMAND ${MSGFMT_EXECUTABLE} -c ${pofile} -o ${mofile}
            DEPENDS ${pofile} ${alinguas})
        install(FILES ${mofile} DESTINATION ${localedir}/${lang}/LC_MESSAGES
                RENAME ${podomain}.mo)
        set(mofiles ${mofiles} ${mofile})
    endforeach()
    add_custom_target(${target} ALL DEPENDS ${mofiles} ${alinguas})

endmacro()


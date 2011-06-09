# TODO: Add doc comments for all this stuff.


function(GET_CURRENT_SOURCE_SUBDIR subdirvar)
    set(argn ${ARGN})

    string(REPLACE ${CMAKE_SOURCE_DIR}/ "" subdir
                   ${CMAKE_CURRENT_SOURCE_DIR})

    if(${ARGC} GREATER 1)
        string(REPLACE "/" ";" subdirlst ${subdir})
        list(LENGTH subdirlst subdepth)
        set(start 0)
        if(${ARGC} GREATER 1)
            list(GET argn 0 start)
            string(REGEX MATCH "^-" isneg ${start})
            if(isneg)
                math(EXPR start "${subdepth} ${start}")
            endif()
        endif()
        set(end ${subdepth})
        if(${ARGC} GREATER 2)
            list(GET argn 1 end)
            string(REGEX MATCH "^-" isneg ${end})
            if(isneg)
                math(EXPR end "${subdepth} ${end}")
            endif()
        endif()
        set(subdir "")
        set(i 0)
        math(EXPR startm1 "${start} - 1")
        math(EXPR endp1 "${end} + 1")
        foreach(cdir ${subdirlst})
            if(i GREATER startm1 AND i LESS endp1)
                if(subdir)
                    set(subdir "${subdir}/${cdir}")
                else()
                    set(subdir "${cdir}")
                endif()
            endif()
            math(EXPR i "${i} + 1")
        endforeach()
    endif()

    set(${subdirvar} "${subdir}" PARENT_SCOPE)

endfunction()


macro(LINK_INSTALL_SCRIPTS instdir linkdir)
    set(scripts ${ARGN})

    # If install directory is a relative path, prepend install prefix.
    if(NOT IS_ABSOLUTE ${instdir})
        set(instdir ${CMAKE_INSTALL_PREFIX}/${instdir})
    endif()

    # Determine base name for targets.
    get_current_source_subdir(srcsubdir)
    string(REPLACE "/" "-" targbase ${srcsubdir})

    if(UNIX)
        # On UNIX platforms, make symlinks to point as installed.
        set(scriptlinks)
        foreach(script ${scripts})
            get_filename_component(scriptname ${script} NAME)
            get_filename_component(scriptnamewe ${script} NAME_WE)
            set(scriptlinkdir ${CMAKE_CURRENT_BINARY_DIR}/bin)
            set(scriptlink ${scriptlinkdir}/${scriptnamewe})
            set(scriptlinks ${scriptlinks} ${scriptlink})
            add_custom_command(OUTPUT ${scriptlink}
                               COMMAND mkdir -p ${scriptlinkdir}
                               COMMAND ln -sf
                                       ${instdir}/${scriptname}
                                       ${scriptlink}
                               DEPENDS ${script})
            install(PROGRAMS ${script} DESTINATION ${instdir})
            install(PROGRAMS ${scriptlink} DESTINATION ${linkdir})
        endforeach()
        add_custom_target(${targbase}-links ALL DEPENDS ${scriptlinks})
    else()
        # On non-UNIX platforms, put scripts directly into linkdir instead.
        # FIXME: Batch files for WIN32?
        foreach(script ${scripts})
            get_filename_component(scriptnamewe ${script} NAME_WE)
            install(PROGRAMS ${script} DESTINATION ${linkdir}
                    RENAME ${scriptnamewe})
        endforeach()
    endif()

endmacro()



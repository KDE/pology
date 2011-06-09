# TODO: Add doc comments for all this stuff.

if(NOT POLOGY_LIB_DIR)
    find_package(Pology)
endif()

if(NOT plt_target_count)
    set(plt_target_count 1)
endif()


set(pl_compsyn_script ${CMAKE_BINARY_DIR}/pology_compsyn.py)
file(WRITE ${pl_compsyn_script} "
import sys, pology.synder
sdfile, sdcfile = sys.argv[1:]
pology.synder.compile_file(sdfile, sdcfile, doraise=True)
")


macro(INSTALL_SYNDER_FILES instdir)
    set(sdfiles ${ARGN})

    if(NOT PYTHON2_EXECUTABLE)
        message(FATAL_ERROR "PYTHON2_EXECUTABLE is not set.")
    endif()

    string(REPLACE ${CMAKE_SOURCE_DIR}/ "" srcsubdir
                   ${CMAKE_CURRENT_SOURCE_DIR})
    string(REPLACE "/" "-" targbase ${srcsubdir})
    set(target "${targbase}-plt${plt_target_count}-compile-synder-files")
    math(EXPR plt_target_count "${plt_target_count} + 1")

    set(sdcfiles)
    foreach(sdfile ${sdfiles})
        if(NOT IS_ABSOLUTE ${sdfile})
            set(sdfilerel ${sdfile})
            set(sdfile ${CMAKE_CURRENT_SOURCE_DIR}/${sdfilerel})
            set(sdcfile ${CMAKE_CURRENT_BINARY_DIR}/${sdfilerel}c)
        else()
            set(sdcfile ${sdfile}c)
        endif()
        add_custom_command(OUTPUT ${sdcfile}
                           COMMAND ${PYTHON2_EXECUTABLE} -B ${pl_compsyn_script}
                                   ${sdfile} ${sdcfile}
                           DEPENDS ${sdfile})
        set(sdcfiles ${sdcfiles} ${sdcfile})
    endforeach()
    add_custom_target(${target} ALL DEPENDS ${sdcfiles})

    install(FILES ${sdfiles} DESTINATION ${instdir})
    install(FILES ${sdcfiles} DESTINATION ${instdir})

endmacro()



# TODO: Add doc comments for all this stuff.

if(NOT PYTHON2_EXECUTABLE)
    find_package(Python2 2)
endif()

if(NOT py2t_target_count)
    set(py2t_target_count 1)
endif()


set(py_compfile_script ${CMAKE_BINARY_DIR}/python2_compfile.py)
file(WRITE ${py_compfile_script} "
import os, sys, py_compile
pyfile, pycfile = sys.argv[1:]
py_compile.compile(pyfile, pycfile, doraise=True)
")


macro(INSTALL_PYTHON2_MODULE_FILES pkgdirpath)
    set(pyfiles ${ARGN})

    if(IS_ABSOLUTE pkgdirpath)
        message(FATAL_ERROR
            "Installation directory for Python modules must be "
            "a relative path (subdirectory of PYTHON2_PACKAGES_DIR).")
    endif()

    set(instdir ${PYTHON2_PACKAGES_DIR}/${pkgdirpath})

    string(REPLACE ${CMAKE_SOURCE_DIR}/ "" srcsubdir
                   ${CMAKE_CURRENT_SOURCE_DIR})
    string(REPLACE "/" "-" targbase ${srcsubdir})
    set(target "${targbase}-plt${py2t_target_count}-compile-python2-files")
    math(EXPR py2t_target_count "${py2t_target_count} + 1")

    set(pycfiles)
    foreach(pyfile ${pyfiles})
        if(NOT IS_ABSOLUTE ${pyfile})
            set(pyfilerel ${pyfile})
            set(pyfile ${CMAKE_CURRENT_SOURCE_DIR}/${pyfilerel})
            set(pycfile ${CMAKE_CURRENT_BINARY_DIR}/${pyfilerel}c)
        else()
            set(pycfile ${pyfile}c)
        endif()
        add_custom_command(OUTPUT ${pycfile}
                           COMMAND ${PYTHON2_EXECUTABLE} ${py_compfile_script}
                                   ${pyfile} ${pycfile}
                           DEPENDS ${pyfile})
        set(pycfiles ${pycfiles} ${pycfile})
    endforeach()
    add_custom_target(${target} ALL DEPENDS ${pycfiles})

    install(FILES ${pyfiles} DESTINATION ${instdir})
    install(FILES ${pycfiles} DESTINATION ${instdir})

endmacro()



# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

set(py_version_script ${CMAKE_BINARY_DIR}/python2_version.py)
file(WRITE ${py_version_script} "
import sys
sys.stdout.write('.'.join(map(str, sys.version_info[:3])))
")

set(py_pkgdir_script ${CMAKE_BINARY_DIR}/python2_pkgdir.py)
file(WRITE ${py_pkgdir_script} "
import sys, distutils.sysconfig
sys.stdout.write(distutils.sysconfig.get_python_lib())
")

if(NOT PYTHON2_EXECUTABLE)
    find_program(PYTHON2_EXECUTABLE NAMES python2 python)
    message(STATUS
        "Looking for Python 2 executable "
        "(use -DPYTHON2_EXECUTABLE= to set manually)...")
else()
    if(NOT EXISTS ${PYTHON2_EXECUTABLE})
        set(PYTHON2_EXECUTABLE no)
    endif()
endif()

if(PYTHON2_EXECUTABLE)
    execute_process(COMMAND ${PYTHON2_EXECUTABLE} ${py_version_script}
                    OUTPUT_VARIABLE PYTHON2_VERSION)

    if(NOT PYTHON2_PACKAGES_DIR)
        set(foo ${CMAKE_CURRENT_LIST_DIR})
        message(STATUS
            "Looking for Python 2 packages directory "
            "(use -DPYTHON2_PACKAGES_DIR= to set manually)...")
        execute_process(COMMAND ${PYTHON2_EXECUTABLE} ${py_pkgdir_script}
                        OUTPUT_VARIABLE PYTHON2_PACKAGES_DIR)
        if(PYTHON2_PACKAGES_DIR)
            message(STATUS
                "Found Python 2 packages directory: ${PYTHON2_PACKAGES_DIR}")
        endif()
    else()
        if(NOT IS_DIRECTORY ${PYTHON2_PACKAGES_DIR})
            set(PYTHON2_PACKAGES_DIR no)
        endif()
    endif()

    set(PYTHON2_PACKAGES_DIR ${PYTHON2_PACKAGES_DIR}
        CACHE PATH "Python 2 packages directory.")
endif()

find_package_handle_standard_args(Python2
    REQUIRED_VARS PYTHON2_EXECUTABLE PYTHON2_PACKAGES_DIR
    VERSION_VAR PYTHON2_VERSION
)

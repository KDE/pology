# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

set(py_version_script ${CMAKE_BINARY_DIR}/python3_version.py)
file(WRITE ${py_version_script} "
import sys
sys.stdout.write('.'.join(map(str, sys.version_info[:3])))
")

set(py_pkgdir_script ${CMAKE_BINARY_DIR}/python3_pkgdir.py)
file(WRITE ${py_pkgdir_script} "
import sys, distutils.sysconfig
sys.stdout.write(distutils.sysconfig.get_python_lib())
")

if(NOT PYTHON3_EXECUTABLE)
    find_program(PYTHON3_EXECUTABLE NAMES python3 python)
    message(STATUS
        "Looking for Python 3 executable "
        "(use -DPYTHON3_EXECUTABLE= to set manually)...")
else()
    if(NOT EXISTS ${PYTHON3_EXECUTABLE})
        set(PYTHON3_EXECUTABLE no)
    endif()
endif()

if(PYTHON3_EXECUTABLE)
    execute_process(COMMAND ${PYTHON3_EXECUTABLE} ${py_version_script}
                    OUTPUT_VARIABLE PYTHON3_VERSION)

    if(NOT PYTHON3_PACKAGES_DIR)
        set(foo ${CMAKE_CURRENT_LIST_DIR})
        message(STATUS
            "Looking for Python 3 packages directory "
            "(use -DPYTHON3_PACKAGES_DIR= to set manually)...")
        execute_process(COMMAND ${PYTHON3_EXECUTABLE} ${py_pkgdir_script}
                        OUTPUT_VARIABLE PYTHON3_PACKAGES_DIR)
        if(PYTHON3_PACKAGES_DIR)
            message(STATUS
                "Found Python 3 packages directory: ${PYTHON3_PACKAGES_DIR}")
        endif()
    else()
        if(NOT IS_DIRECTORY ${PYTHON3_PACKAGES_DIR})
            set(PYTHON3_PACKAGES_DIR no)
        endif()
    endif()

    set(PYTHON3_PACKAGES_DIR ${PYTHON3_PACKAGES_DIR}
        CACHE PATH "Python 3 packages directory.")
endif()

find_package_handle_standard_args(Python3
    REQUIRED_VARS PYTHON3_EXECUTABLE PYTHON3_PACKAGES_DIR
    VERSION_VAR PYTHON3_VERSION
)

# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

set(pl_import_script ${CMAKE_BINARY_DIR}/pology_import.py)
file(WRITE ${pl_import_script} "
import sys, pology
sys.stdout.write(pology.__path__[0])
")

set(pl_version_script ${CMAKE_BINARY_DIR}/pology_version.py)
file(WRITE ${pl_version_script} "
import sys, pology
sys.stdout.write('.'.join(map(str, pology.version_info()[:3])))
")

set(pl_datadir_script ${CMAKE_BINARY_DIR}/pology_datadir.py)
file(WRITE ${pl_datadir_script} "
import sys, pology
sys.stdout.write(pology.datadir())
")

if(NOT PYTHON2_EXECUTABLE)
    find_package(Python2 2.5)
endif()

message(STATUS "Looking for Pology Python library...")
execute_process(COMMAND ${PYTHON2_EXECUTABLE} -B ${pl_import_script}
                OUTPUT_VARIABLE POLOGY_LIB_DIR)

if(POLOGY_LIB_DIR)
    execute_process(COMMAND ${PYTHON2_EXECUTABLE} -B ${pl_version_script}
                    OUTPUT_VARIABLE POLOGY_VERSION)

    if(NOT POLOGY_DATA_DIR)
        message(STATUS "Looking for Pology data directory...")
        execute_process(COMMAND ${PYTHON2_EXECUTABLE} -B ${pl_datadir_script}
                        OUTPUT_VARIABLE POLOGY_DATA_DIR)
        if(POLOGY_DATA_DIR)
            message(STATUS
                "Found Pology data directory: ${POLOGY_DATA_DIR}")
        endif()
    else()
        if(NOT IS_DIRECTORY ${POLOGY_DATA_DIR})
            set(POLOGY_DATA_DIR no)
        endif()
    endif()

    set(POLOGY_DATA_DIR ${POLOGY_DATA_DIR}
        CACHE PATH "Pology data directory.")
endif()

find_package_handle_standard_args(Pology
    REQUIRED_VARS POLOGY_LIB_DIR POLOGY_DATA_DIR
    VERSION_VAR POLOGY_VERSION
)

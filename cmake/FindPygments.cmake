# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

if(NOT PYGMENTS_EXECUTABLE)
    find_program(PYGMENTS_EXECUTABLE NAMES pygmentize)
    message(STATUS
        "Looking for Pygments executable "
        "(use -DPYGMENTS_EXECUTABLE= to set manually)...")
else()
    if(NOT EXISTS ${PYGMENTS_EXECUTABLE})
        set(PYGMENTS_EXECUTABLE no)
    endif()
endif()

if(PYGMENTS_EXECUTABLE)
    set(env_lc_all $ENV{LC_ALL})
    set(ENV{LC_ALL} "C")
    execute_process(COMMAND ${PYGMENTS_EXECUTABLE} -V
                    OUTPUT_VARIABLE stdout)
    string(REGEX REPLACE ".* ([0-9]+\\.[0-9]+(\\.[0-9]+)?).*" "\\1"
                         PYGMENTS_VERSION "${stdout}")
    set(ENV{LC_ALL} ${env_lc_all})
endif()

find_package_handle_standard_args(Pygments
    REQUIRED_VARS PYGMENTS_EXECUTABLE
    VERSION_VAR PYGMENTS_VERSION
)

# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

if(NOT MSGFMT_EXECUTABLE)
    find_program(MSGFMT_EXECUTABLE NAMES msgfmt)
    message(STATUS
        "Looking for msgfmt "
        "(use -DMSGFMT_EXECUTABLE= to set manually)...")
else()
    if(NOT EXISTS ${MSGFMT_EXECUTABLE})
        set(MSGFMT_EXECUTABLE no)
    endif()
endif()

if(MSGFMT_EXECUTABLE)
    set(env_lc_all $ENV{LC_ALL})
    set(ENV{LC_ALL} "C")
    execute_process(COMMAND ${MSGFMT_EXECUTABLE} --version
                    OUTPUT_VARIABLE stdout)
    string(REGEX REPLACE ".* ([0-9]+\\.[0-9]+(\\.[0-9]+)?).*" "\\1"
                         MSGFMT_VERSION "${stdout}")
    set(ENV{LC_ALL} ${env_lc_all})
endif()

find_package_handle_standard_args(Msgfmt
    REQUIRED_VARS MSGFMT_EXECUTABLE
    VERSION_VAR MSGFMT_VERSION
)

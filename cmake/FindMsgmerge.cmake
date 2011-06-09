# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

if(NOT MSGMERGE_EXECUTABLE)
    find_program(MSGMERGE_EXECUTABLE NAMES msgmerge)
    message(STATUS
        "Looking for msgmerge "
        "(use -DMSGMERGE_EXECUTABLE= to set manually)...")
else()
    if(NOT EXISTS ${MSGMERGE_EXECUTABLE})
        set(MSGMERGE_EXECUTABLE no)
    endif()
endif()

if(MSGMERGE_EXECUTABLE)
    set(env_lc_all $ENV{LC_ALL})
    set(ENV{LC_ALL} "C")
    execute_process(COMMAND ${MSGMERGE_EXECUTABLE} --version
                    OUTPUT_VARIABLE stdout)
    string(REGEX REPLACE ".* ([0-9]+\\.[0-9]+(\\.[0-9]+)?).*" "\\1"
                         MSGMERGE_VERSION "${stdout}")
    set(ENV{LC_ALL} ${env_lc_all})
endif()

find_package_handle_standard_args(Msgmerge
    REQUIRED_VARS MSGMERGE_EXECUTABLE
    VERSION_VAR MSGMERGE_VERSION
)

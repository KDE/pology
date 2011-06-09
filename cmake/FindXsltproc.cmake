# TODO: Add doc comments.

include(FindPackageHandleStandardArgs)

if(NOT XSLTPROC_EXECUTABLE)
    find_program(XSLTPROC_EXECUTABLE NAMES xsltproc)
    message(STATUS
        "Looking for xsltproc "
        "(use -DXSLTPROC_EXECUTABLE= to set manually)...")
else()
    if(NOT EXISTS ${XSLTPROC_EXECUTABLE})
        set(XSLTPROC_EXECUTABLE no)
    endif()
endif()

find_package_handle_standard_args(Xsltproc
  REQUIRED_VARS XSLTPROC_EXECUTABLE
)

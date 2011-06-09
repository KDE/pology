if(NOT CAN_BUILD_PO)
    return()
endif()

install_po_domain(pology LINGUAS ${MO_INSTALL_DIR})


set(files
    docbook4.l1
    html.entities
    html.l1
    kuit.l1
    kuit.entities
    pango.l1
    qtrich.l1
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

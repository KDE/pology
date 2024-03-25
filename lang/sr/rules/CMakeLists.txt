set(files
    domain.rules
    orthography.rules
    puretext.filters
    techne-kde.rules
    terminology-kde.rules
    terminology.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

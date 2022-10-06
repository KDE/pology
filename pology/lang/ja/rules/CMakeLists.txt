set(files
    common-misktakes.rules
    puretext.filters
    style.rules
    terminology-extra.rules
    terminology.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

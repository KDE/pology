set(files
    filter.include    
    controlledLang.rules
    terminology.rules
    kde.rules
    gnome.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

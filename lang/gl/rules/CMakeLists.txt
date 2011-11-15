set(files
    filter.include    
    controlledLang.rules
    terminology.rules
    kde_choices.rules
    xfceGnome_choices.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

set(files
    filter.include
    controlledLang.rules
    expression.rules
    gnome.rules
    kde.rules
    terminology.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

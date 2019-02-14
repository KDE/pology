set(files
    expression.rules
    filter.include
    gnome.rules
    kde.rules
    n11n.rules
    terminology.rules
    trasno.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

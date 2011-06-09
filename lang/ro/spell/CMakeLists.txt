set(files
    computer.aspell
    finance.aspell
    kde.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

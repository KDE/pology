set(files
    geography.aspell
    kstars.aspell
    misc.aspell
    names.aspell
    short.aspell
    software.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

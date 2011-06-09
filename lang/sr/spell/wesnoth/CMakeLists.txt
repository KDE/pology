set(files
    general.aspell
    names.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

add_subdirectory(noent)

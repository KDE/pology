set(files
    dict.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

add_subdirectory(kde)
add_subdirectory(wesnoth)

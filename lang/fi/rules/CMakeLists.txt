set(files
    domain.rules
    false-friends.rules
    kde-fi-terms.rules
    orthography.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

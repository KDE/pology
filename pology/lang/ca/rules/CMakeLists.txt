set(files
    barbarism.rules
    common-mistakes.rules
    doc-entities.rules
    false-friends.rules
    filter.include
    html-tag.rules
    kde-ca-team.rules
    keys.rules
    typography.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

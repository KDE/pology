set(files
    common-mistakes.rules
    doc-entities.rules
    doc-headers.rules
    koffice.rules.disabled
    team-choices.rules
    typography.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

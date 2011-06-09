set(files
    english.rules
    grammar.rules
    ortography.rules
    puretext.filters
    team-choices.rules
    technical.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

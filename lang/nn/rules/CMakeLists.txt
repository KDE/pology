set(files
    application-names.rules
    bokmal-words.rules
    domain.rules
    english.rules
    grammar.rules
    kde.rules
    ortography.rules
    puretext.filters
    team-choices.rules
    technical.rules
    unfiltered.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

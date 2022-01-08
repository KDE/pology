set(files
    domain.rules
    english.rules
    grammar.rules
    bokmal-words.rules
    kde.rules
    ortography.rules
    puretext.filters
    team-choices.rules
    technical.rules
    unfiltered.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

set(files
    filter.include
    being-polite.rules.disabled
    common-mistakes.rules
    false-friends.rules
    gerund-detector.rules.disabled
    grammar.rules
    kde-l10n-es-proposed.rules
    kde-l10n-es.rules
    paired-words.rules
    paragraph-begin.rules
    paragraph-end.rules
    translators.rules
    typography.rules
    user-interface.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

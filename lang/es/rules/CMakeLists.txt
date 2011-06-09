set(files
    being-polite.rules.disabled
    common-mistakes.rules
    false-friends.rules
    filter.include
    gerund-detector.rules.disabled
    glosario-kde-l10n-es-proposed.rules
    glosario-kde-l10n-es.rules
    paired-words.rules
    paragraph-begin.rules
    paragraph-end.rules
    translators.rules
    typography.rules
    user-interface.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

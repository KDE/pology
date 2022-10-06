set(files
    all.rules
    check-spell.rules.disabled
    letter-yo.rules
    menu-names.rules
    unstable.rules.disabled
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

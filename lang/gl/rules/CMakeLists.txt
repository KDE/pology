set(files
    controlledLang_gl.rules
    filter.include
    frequentExpressions.rules
    kde_choices.rules
    terminology.rules.blocked
    terminology_trasnadas_dual.rules
    terminology_trasnadas.rules
    xfceGnome_choices.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

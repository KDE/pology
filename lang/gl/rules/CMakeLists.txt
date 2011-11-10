set(files
    filter.include    
    controlledLang_trasnadas.rules
    terminology_trasnadas.rules
    terminology_trasnadas_dual.rules
    controlledLang_gl.rules
    frequentExpressions.rules
    kde_choices.rules
    xfceGnome_choices.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

set(files
    computingTerms.aspell
    galicianWords.aspell
    softwareProducts.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

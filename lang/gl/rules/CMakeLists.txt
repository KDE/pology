set(files
    antigas.rules
    filter.include
    outras.rules
    rag.rules
    trasno.rules
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

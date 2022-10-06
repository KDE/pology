set(sieves
    fill_doc_date_kde.py
)
get_current_source_subdir(srcsubdir)
install(FILES ${sieves} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

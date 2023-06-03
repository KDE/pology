set(sieves
    setUbsp.py
    setApostrophe.py
)
get_current_source_subdir(srcsubdir)
install(FILES ${sieves} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

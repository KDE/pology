set(files
    e-infinitiv.dat
    klammeformer.dat
    README
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

set(files
    e-infinitiv.dat
    imperativfeil.dat
    klammeformer.dat
    subst-mask-er.dat
    subst-fem-ar.dat
    README
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

set(files
    e-infinitiv.dat
    bokmal-words.dat
    feil-paradigme.dat
    imperativfeil.dat
    klammeformer.dat
    subst-mask-er.dat
    subst-fem-ar.dat
    unormert.dat
    README
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

set(scripts
    pohybdl.py
    traplint.py
)
get_current_source_subdir(srcsubdir)
link_install_scripts(${DATA_INSTALL_DIR}/${srcsubdir} ${BIN_INSTALL_DIR}
                     ${scripts})

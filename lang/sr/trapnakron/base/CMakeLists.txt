set(sdfiles
    aff.sd
    afflive.sd
)
get_current_source_subdir(srcsubdir)
install_synder_files(${DATA_INSTALL_DIR}/${srcsubdir} ${sdfiles})

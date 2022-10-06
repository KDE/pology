set(sdfiles
    aggregates.sd
    calendar.sd
    credits.sd
    dotdesktop.sd
    fontsupp.sd
    places.sd
)
get_current_source_subdir(srcsubdir)
install_synder_files(${DATA_INSTALL_DIR}/${srcsubdir} ${sdfiles})

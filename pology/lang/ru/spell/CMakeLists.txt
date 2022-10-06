set(files
    abbr.aspell
    artwork-names.aspell
    country-names.aspell
    currency-names.aspell
    custom-names.aspell
    developer-names.aspell
    dict.aspell
    gnome-apps.aspell
    kalzium.aspell
    kdenlive.aspell
    kopete.aspell
    localization-names.aspell
    microblogging.aspell
    music-genres.aspell
    torrents.aspell
    translator-names.aspell
    units.aspell
    units-generated.aspell
    writing-systems.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

add_subdirectory(hack)

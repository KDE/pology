set(files
    astro.aspell
    chemical_compounds.aspell
    colors.aspell
    countries.aspell
    currency_units.aspell
    dev.aspell
    elements.aspell
    fonts.aspell
    games.aspell
    general.aspell
    graphics.aspell
    instruments.aspell
    kde.aspell
    languages.aspell
    moji.aspell
    multimedia.aspell
    music.aspell
    network.aspell
    proper_names.aspell
    science.aspell
    uiterms.aspell
    units.aspell
)
get_current_source_subdir(srcsubdir)
install(FILES ${files} DESTINATION ${DATA_INSTALL_DIR}/${srcsubdir})

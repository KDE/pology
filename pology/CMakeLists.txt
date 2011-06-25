# Configure paths in __init__.py
set(CONFIG_DATADIR ${DATA_INSTALL_DIR})
set(CONFIG_LOCALEDIR ${MO_INSTALL_DIR})
set(CONFIG_VERSION ${PROJECT_VERSION})
configure_file(__init__.py ${CMAKE_CURRENT_BINARY_DIR}/__init__.py @ONLY)

set(modules
    ${CMAKE_CURRENT_BINARY_DIR}/__init__.py # configured
    ascript.py
    bpatterns.py
    catalog.py
    colors.py
    comments.py
    config.py
    diff.py
    entities.py
    escape.py
    fsops.py
    getfunc.py
    gtxtools.py
    header.py
    markup.py
    match.py
    merge.py
    message.py
    monitored.py
    msgreport.py
    multi.py
    noop.py
    normalize.py
    remove.py
    report.py
    resolve.py
    rules.py
    sieve.py
    spell.py
    split.py
    stdcmdopt.py
    subcmd.py
    synder.py
    tabulate.py
    timeout.py
    uiref.py
    vcs.py
    wrap.py
)
get_current_source_subdir(srcsubdir)
install_python2_module_files(${srcsubdir} ${modules})

add_subdirectory(proj)
add_subdirectory(lang)
add_subdirectory(internal)
add_subdirectory(external)

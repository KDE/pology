set(modules
    __init__.py
    patternAccents.py
    patternEntities.py
)
get_current_source_subdir(srcsubdir)
install_python2_module_files(${srcsubdir} ${modules})

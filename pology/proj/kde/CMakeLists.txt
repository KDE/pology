set(modules
    __init__.py
    cattype.py
    header.py
)
get_current_source_subdir(srcsubdir)
install_python2_module_files(${srcsubdir} ${modules})

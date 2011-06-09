set(modules
    __init__.py
    compare_with_original.py
    remove_subs.py
)
get_current_source_subdir(srcsubdir)
install_python2_module_files(${srcsubdir} ${modules})

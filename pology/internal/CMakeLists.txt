set(modules
    __init__.py
    poediffpatch.py
)
get_current_source_subdir(srcsubdir)
install_python3_module_files(${srcsubdir} ${modules})

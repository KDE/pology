set(modules
    __init__.py
    accents.py
    charsets.py
    checks.py
    nobr.py
    reduce.py
    trapnakron.py
    trapres.py
    uiref.py
    wconv.py
)
get_current_source_subdir(srcsubdir)
install_python2_module_files(${srcsubdir} ${modules})

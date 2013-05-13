set(modules
    __init__.py
)
get_current_source_subdir(srcsubdir)
install_python2_module_files(${srcsubdir} ${modules})

add_subdirectory(es)
add_subdirectory(fr)
add_subdirectory(ja)
add_subdirectory(nb)
add_subdirectory(nn)
add_subdirectory(sr)

set(scripts
    normalize-aspell-word-list.py
    poascribe.py
    podescprob.py
    poediff.py
    poepatch.py
    poextinj.py
    pomtrans.py
    porewrap.py
    poselfmerge.py
    posieve.py
    posummit.py
)
get_current_source_subdir(srcsubdir)
link_install_scripts(${DATA_INSTALL_DIR}/${srcsubdir} ${BIN_INSTALL_DIR}
                     ${scripts})

<?php

$fallback_lang = "en_US";

function _subs_args ($text, $args)
{
    if ($args) {
        array_unshift($args, $text);
        return call_user_func_array("sprintf", $args);
    } else {
        return $text;
    }
    // NOTE: Text is not pulled through sprintf in case of zero arguments,
    // for the following reason. If the original text did not contain
    // any formatting directives, its message in the PO file will not be given
    // the php-format flag; if the translator then uses % in translation,
    // and the text is pulled through sprintf, kaboom.
}

// Dummy translation calls, for the moment.

// varargs: msgid, ...
function vt_ ()
{
    $args = func_get_args();
    $msgid = array_shift($args);
    $msgstr = $msgid; // dummy
    return _subs_args($msgstr, $args);
}

// varargs: msgctxt, msgid, ...
function vpt_ ()
{
    $args = func_get_args();
    $msgctxt = array_shift($args);
    $msgid = array_shift($args);
    $msgstr = $msgid; // dummy
    return _subs_args($msgstr, $args);
}

// varargs: msgid, msgid_plural, n, ...
function vnt_ ()
{
    $args = func_get_args();
    $msgid = array_shift($args);
    $msgid_plural = array_shift($args);
    $n = array_shift($args);
    $msgstr = $n == 1 ? $msgid : $msgid_plural; // dummy
    return _subs_args($msgstr, $args);
}

// varargs: msgctxt, msgid, msgid_plural, n, ...
function vpnt_ ()
{
    $args = func_get_args();
    $msgctxt = array_shift($args);
    $msgid = array_shift($args);
    $msgid_plural = array_shift($args);
    $n = array_shift($args);
    $msgstr = $n == 1 ? $msgid : $msgid_plural; // dummy
    return _subs_args($msgstr, $args);
}

// varargs: msgid, ...
function t_ ()
{
    echo call_user_func_array("vt_", func_get_args()) . "\n";
}

// varargs: msgctxt, msgid, ...
function pt_ ()
{
    echo call_user_func_array("vpt_", func_get_args()) . "\n";
}

// varargs: msgid, msgid_plural, n, ...
function nt_ ()
{
    echo call_user_func_array("vnt_", func_get_args()) . "\n";
}

// varargs: msgctxt, msgid, msgid_plural, n, ...
function pnt_ ()
{
    echo call_user_func_array("vpnt_", func_get_args()) . "\n";
}

// Return path for given language if it exists,
// otherwise return path for fallback language.
// $pathbase should contain one %s printf-directive,
// which is replaced by the language code to construct the final path.
function path_for_lang ($pathbase, $lang)
{
    $path = sprintf($pathbase, $lang);
    if (!file_exists($path)) {
        global $fallback_lang;
        $path = sprintf($pathbase, $fallback_lang);
    }
    return $path;
}

// Some global translation pieces.
$listsep = vpt_("separator when listing items in text", ", ");

?>

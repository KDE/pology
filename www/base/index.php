<?php
include("i18n.inc");
$page_title = vpt_("page title", "Pology — The Study of PO");
include("header.inc");

$rooturl = sprintf("http://%s%s",
                   $_SERVER["SERVER_NAME"],
                   dirname($_SERVER["PHP_SELF"]));

// ========================================
t_("<h1>Pology — The Study of PO</h1>");

t_("<p class='first'>Pology is a Python library and collection of command-line tools for in-depth processing of PO files, the translation file format of the <a href='%s'>GNU Gettext</a> software translation system. Pology functionality ranges from precision operations on individual PO messages, to cross-file operations on large collections of PO files.</p>",
   "http://www.gnu.org/s/gettext/");

t_("<p>A distinguishing aspect of Pology is that no attempt is made to handle arbitrary translation file formats, as is typical of many translation tools. Pology can thus take advantage not only of all technical aspects of the PO format, but also of the established conventions and workflows revolving around it and Gettext in general. This focus is present on all levels, from the end-user commands to the library file format abstractions.</p>");

// ========================================
t_("<h2>Elements</h2>");

t_("<p class='first'>More prominent elements of Pology functionality currently include:</p>".
   "<ul>%s</ul>", "\n".
   vt_("<li><p>Examination and in-place modification of collections of PO files (the <code>posieve</code> command). Through unified batch-processing interface, various tools (\"sieves\") can be applied to messages in PO files.</p></li>")."\n".
   vt_("<li><p>Format-aware diffing and patching of PO files (the <code>poediff</code> and <code>poepatch</code> commands). Line-oriented diffs/patches are rather inadequate for PO files, so Pology provides diffing and patching which specifically takes into account elements of the PO format.</p></li>")."\n".
   vt_("<li><p>Handling two or more translation branches (the <code>posummit</code> command). When the software project has parallel or semi-parallel stable and development branches (or even more branches), \"summiting\" makes it possible for translators to always work on a single set of PO files, with modifications being automatically propagated to required branches.</p></li>")."\n".
   vt_("<li><p>Fine-grained asynchronous review workflow (the <code>poascribe</code> command). Typical translation review workflow is split into synchronous stages (submit, review, approve, commit), sometimes requiring whole files to be reviewed at once before committing. Pology instead provides fully asynchronous review process, which functions on the PO message level, and allows any other tools to be used as usual.</p></li>")."\n".
   vt_("<li><p>Custom translation validation. Users can write validation rules for particular languages and projects, which can then be applied in various contexts (e.g. through <code>posieve</code> or <code>posummit</code> commands). Pology distribution contains internal validation rules for some languages and projects, and more can be contributed at any time.</p></li>")."\n".
   vt_("<li><p>Language- and project-specific support. Many elements of Pology are ready to accept specific support for different languages, and different translation projects (\"environments\") within one language. This includes, for example, spelling dictionaries, translation validation rules, and library modules.</p></li>")."\n");

// ========================================
t_("<h2>Availability</h2>");

$ver_curr = "0.10";
$ver_old = array();

$relurl_base = sprintf("%s/release/pology-%%s.tar.gz", $rooturl);
$relurl_curr = sprintf($relurl_base, $ver_curr);
t_("<p class='first'>Current release is %s and can be downloaded from here:</p>".
   "<div class='inset'><p><code><a href='%s'>%s</a></code></p></div>",
   $ver_curr, $relurl_curr, $relurl_curr);
if ($ver_old) {
    $verurlfmt = array();
    foreach ($ver_old as $ver) {
        $relurl = sprintf($relurl_base, $ver);
        $verurlfmt[] = sprintf("<a href='%s'>%s</a>", $relurl, $ver);
    }
    $verlistfmt = implode($listsep, $verurlfmt);
    t_("<p>Some earlier releases are also available: %s.</p>",
       $verlistfmt);
}

t_("<p>Pology has been mostly tested on GNU/Linux-based operating systems. The software which Pology depends on, as well as most of the optional software for additional functionality, is already packaged on these platforms. Pology has been reported to run on contemporary Windows systems, albeit from the source tree only and likely with some reduction in functionality.</p>");

$repourl_dvl = "svn://anonsvn.kde.org/home/kde/trunk/l10n-support/pology";
$webrepourl_dvl = "http://websvn.kde.org/trunk/l10n-support/pology/";
t_("<p>Latest development code can be obtained from a Subversion repository:</p>".
   "<div class='inset'><p><code>svn checkout %s</code></p></div>".
   "<p class='cont'>or browsed through a web interface at:</p>".
   "<div class='inset'><p><code><a href='%s'>%s</a></code></p></div>",
   $repourl_dvl, $webrepourl_dvl, $webrepourl_dvl);

// ========================================
t_("<h2>Documentation</h2>");

$lang = "en_US"; # FIXME: Detect from user.

$manurl_chunk = path_for_lang(sprintf("%s/doc/user/%%s/index.html", $rooturl),
                              $lang);
$manurl_mono = path_for_lang(sprintf("%s/doc/user/%%s/index-mono.html", $rooturl),
                             $lang);
t_("<p class='first'>The user manual is contained within Pology distribution, and can be built from source if all documentation-generation dependencies are installed. The user manual for current Pology release can be browsed on-line:</p>".
   "<div class='inset'>".
   "<p><code><a href='%s'>%s</a></code> (by chapter)</p>".
   "<p><code><a href='%s'>%s</a></code> (single page)</p>".
   "</div>",
   $manurl_chunk, $manurl_chunk, $manurl_mono, $manurl_mono);

$langmans = array(
    "sr" => vpt_("language", "Serbian"),
);
$langmansfmt = array();
foreach ($langmans as $lc => $ln) {
    $langmanurl_chunk = sprintf("%s/doc/lang/%s/%s/index.html",
                                $rooturl, $lc, $lc);
    $langmanurl_mono = sprintf("%s/doc/lang/%s/%s/index-mono.html",
                               $rooturl, $lc, $lc);
    $langmansfmt[] = vpt_("language manual, one chapter by page ".
                          "or all on single page",
                          "%s <a href='%s'>by chapter</a>/".
                          "<a href='%s'>single</a>",
                          $ln, $langmanurl_chunk, $langmanurl_mono);
}
$langmanfmt = implode($listsep, $langmansfmt);
t_("<p>There are separate user manuals describing language-specific functionality in Pology, written in corresponding languages. They can be browsed on-line as follows: %s.</p>",
   $langmanfmt);

$apiurl_curr = path_for_lang(sprintf("%s/doc/api/%%s/index.html", $rooturl),
                             $lang);
t_("<p>For programming with Pology, the API reference is also included in the distribution. The online version corresponding to current Pology release can be found here:</p>".
   "<div class='inset'><p><code><a href='%s'>%s</a></code></p></div>",
   $apiurl_curr, $apiurl_curr);

// ========================================
t_("<h2>Contact</h2>");

$mlurl = "http://lists.nedohodnik.net/listinfo.cgi/pology-nedohodnik.net";
t_("<p class='first'>At the moment, all communication should be directed to the Pology mailing list:</p>".
   "<div class='inset'><p><code><a href='%s'>%s</a></code></p></div>".
   "<p class='cont'>This includes questions about usage, development discussion, and bug reports. You do not need to be subscribed to post, but expect some moderation delay in that case.</p>",
   $mlurl, $mlurl);

$mntemail = "caslav.ilic@gmx.net";
t_("<p>Pology maintainer can also be reached directly at: <a href='mailto:Chusslove Illich &lt;%s&gt;'>Chusslove Illich &lt;<code>%s</code>&gt;</a>.</p>",
   $mntemail, $mntemail);

// ========================================
include("footer.inc");
?>

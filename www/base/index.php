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

t_("<p class='first'>Some of the prominent elements of Pology functionality include:</p>".
   "<ul>%s</ul>", "\n".
   vt_("<li><p><em>Examination and in-place modification of collections of PO files</em> (the <code>posieve</code> command). Through unified batch-processing interface, various tools (\"sieves\") can be applied to messages in PO files.</p></li>")."\n".
   vt_("<li><p><em>Format-aware diffing and patching of PO files</em> (the <code>poediff</code> and <code>poepatch</code> commands). Line-oriented diffs/patches are rather inadequate for PO files, so Pology provides diffing and patching which specifically takes into account elements of the PO format.</p></li>")."\n".
   vt_("<li><p><em>Handling two or more translation branches</em> (the <code>posummit</code> command). When the software project has parallel or semi-parallel stable and development branches (or even more branches), \"summiting\" makes it possible for translators to always work on a single set of PO files, with modifications being automatically propagated to required branches.</p></li>")."\n".
   vt_("<li><p><em>Fine-grained asynchronous review workflow</em> (the <code>poascribe</code> command). Typical translation review workflow is split into stages (e.g. submit, review, approve, commit), which are handled by designated team members, and sometimes requires whole files to be reviewed at once. Pology instead provides fully asynchronous review process, where anyone can commit and review at any time, and reviews are recorded per PO message.</p></li>")."\n".
   vt_("<li><p><em>Custom translation validation</em>. Users can write validation rules for particular languages and projects, which can then be applied in various contexts (e.g. through <code>posieve</code> or <code>posummit</code> commands). Pology distribution contains internal validation rules for some languages and projects, and more can be contributed at any time.</p></li>")."\n".
   vt_("<li><p><em>Language- and project-specific support</em>. Many elements of Pology are ready to accept specific support for different languages, and different translation projects (\"environments\") within one language. This includes, for example, spelling dictionaries, translation validation rules, and library modules.</p></li>")."\n");

// ========================================
t_("<h2>Availability</h2>");

$relfile = "pology-0.13.tar.bz2";

$reldir = "release";
t_("<p class='first'>Latest release can be downloaded from here:</p>".
   "<div class='inset'><p><a href='%s'><code>%s</code></a></p></div>".
   "<p class='cont'>Older releases can be found in the <a href='%s'><code>%s</code></a> directory.</p>",
   sprintf("%s/%s/%s", $rooturl, $reldir, $relfile), $relfile,
   sprintf("%s/%s/", $rooturl, $reldir), sprintf("%s/", $reldir));

$repourl_dvl = "svn://anonsvn.kde.org/home/kde/trunk/l10n-support/pology";
$webrepourl_dvl = "http://websvn.kde.org/trunk/l10n-support/pology/";
t_("<p>Latest development code can be obtained from a Subversion repository:</p>".
   "<div class='inset'><p><code>svn checkout %s</code></p></div>".
   "<p class='cont'>or browsed through a <a href='%s'>web interface</a>.</p>",
   $repourl_dvl, $webrepourl_dvl);

t_("<p>Pology has been mostly tested on GNU/Linux-based operating systems. The software which Pology depends on, as well as most of the optional software for additional functionality, is already packaged on these platforms. Pology has been reported to run on contemporary Windows systems, albeit from the source tree only and likely with some reduction in functionality.</p>");

$lcurl = "http://www.gnu.org/copyleft/gpl.html";
t_("<p>Pology is distributed under the terms of <a href='%s'>GNU GPL, version 3</a>.</p>",
    $lcurl);

// ========================================
t_("<h2>Documentation</h2>");

$lang = "en_US"; # FIXME: Detect from user.

$manurl_chunk = path_for_lang(sprintf("%s/doc/user/%%s/index.html", $rooturl),
                              $lang);
$manurl_mono = path_for_lang(sprintf("%s/doc/user/%%s/index-mono.html", $rooturl),
                             $lang);
t_("<p class='first'>The user manual is contained in the Pology distribution, and it will be built from the source if all documentation-generation dependencies are satisfied. The user manual for latest Pology release is available on-line:</p>".
   "<div class='inset'>".
   "<p><a href='%s'>HTML — one page per chapter</a></p>".
   "<p><a href='%s'>HTML — everything on single page</a></p>".
   "</div>",
   $manurl_chunk, $manurl_mono);

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
                          "<a href='%s'>single page</a>",
                          $ln, $langmanurl_chunk, $langmanurl_mono);
}
$langmanfmt = implode($listsep, $langmansfmt);
t_("<p>There are separate user manuals describing language-specific functionality in Pology (written in corresponding languages). They are available on-line as follows: %s.</p>",
   $langmanfmt);

$apiurl_curr = path_for_lang(sprintf("%s/doc/api/%%s/index.html", $rooturl),
                             $lang);
t_("<p>For programming with Pology, the API reference is included in the distribution. The online version for the latest Pology release is here:</p>".
   "<div class='inset'><p><a href='%s'>HTML — one page per node</a></p></div>",
   $apiurl_curr);

// ========================================
t_("<h2>Contact</h2>");

$mlurl = "http://lists.nedohodnik.net/listinfo.cgi/pology-nedohodnik.net";
t_("<p class='first'>At the moment, all communication should be directed to the <a href='%s'>Pology mailing list</a>. This includes questions about usage, development discussion, and bug reports. You do not need to be subscribed to post to the list, but expect some moderation delay in that case.</p>",
   $mlurl);

$mntemail = "caslav.ilic@gmx.net";
t_("<p>Pology maintainer can also be reached directly at: <a href='mailto:Chusslove Illich &lt;%s&gt;'>Chusslove Illich &lt;<code>%s</code>&gt;</a>.</p>",
   $mntemail, $mntemail);

// ========================================
include("footer.inc");
?>

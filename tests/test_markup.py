import html.entities

import pytest

from pology.markup import (_escape_amp_accel, html_entities, html_to_plain,
                           validate_html_l1, xml_to_plain)

@pytest.mark.parametrize(
    "input,output",
    (
        # Digits and Unicode letters can work as accelerator characters.
        ("Choice &1", "Choice &amp;1"),
        ("&save", "&amp;save"),
        ("&Save", "&amp;Save"),
        ("&Პარამეტრი:", "&amp;Პარამეტრი:"),

        # Symbols and Unicode letters cannot work as accelerator characters.
        ("Choose&:", "Choose&:"),
    ),
)
def test_escape_amp_accel(input, output):
    assert _escape_amp_accel(input) == output


@pytest.mark.parametrize(
    "input,output",
    (
        ("Søk\xa0…", "Søk\xa0…"),
    ),
)
def test_xml_to_plain(input, output):
    assert xml_to_plain(input) == output


@pytest.mark.parametrize(
    "input,output",
    (
        ("<article>Text</article>", "Text"),
        ("<figure><img src='x'/><figcaption>Caption</figcaption></figure>",
         "Caption"),
        ("<details><summary>More</summary>Body</details>", "More\n\nBody"),
        ("<section class='x'>A &hellip; B</section>", "A … B"),
        ("<p>Text &mdash; more</p>", "Text — more"),
        ("<audio controls='controls' src='x'></audio>", ""),
        ("<video controls='controls' src='x'></video>", ""),
    ),
)
def test_html_to_plain_html5(input, output):
    assert html_to_plain(input) == output


@pytest.mark.parametrize(
    "text",
    (
        "<article>Text</article>",
        "<figure><img src='x'/></figure>",
        "<time datetime='2026-01-01'>then</time>",
        "<input type='search' placeholder='Find'/>",
        "<section class='x'>A &hellip; B &mdash; C</section>",
    ),
)
def test_validate_html5(text):
    assert validate_html_l1(text, ents={}) == []


@pytest.mark.parametrize(
    "text",
    (
        "<bogus>Text</bogus>",
        "<article bogusattr='x'>Text</article>",
        "Text &bogusent;",
    ),
)
def test_validate_html5_rejects(text):
    assert validate_html_l1(text, ents={}) != []


def test_html5_entities_audit():
    html5_names = set(k[:-1] for k in html.entities.html5 if k.endswith(";"))
    # 'tm' is a legacy name not listed in the HTML5 set.
    assert set(html_entities) <= html5_names | {"tm"}
    assert {"hellip", "mdash", "rarr", "check", "euro"} <= set(html_entities)

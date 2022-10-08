import pytest

from pology.markup import _escape_amp_accel, xml_to_plain

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

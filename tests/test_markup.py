import pytest

from pology.markup import _escape_amp_accel

@pytest.mark.parametrize(
    "input,output",
    (
        # Digits and ASCII letters can work as accelerator characters.
        ("&save", "&amp;save"),
        ("&Save", "&amp;Save"),
        ("Choice &1", "Choice &amp;1"),

        # Symbols and Unicode letters cannot work as accelerator characters.
        ("Choose&:", "Choose&:"),
        ("&Პარამეტრი:", "&Პარამეტრი:"),
    ),
)
def test_escape_amp_accel(input, output):
    assert _escape_amp_accel(input) == output
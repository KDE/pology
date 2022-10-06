import pytest

from pology.markup import _escape_amp_accel

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
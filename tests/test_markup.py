import pytest

from pology.markup import _escape_amp_accel

@pytest.mark.parametrize(
    "input,output",
    (
        ("&Save", "&amp;Save"),
        # Non-Latin characters cannot work as accelerator characters.
        ("&Პარამეტრი:", "&Პარამეტრი:"),
    ),
)
def test_escape_amp_accel(input, output):
    assert _escape_amp_accel(input) == output
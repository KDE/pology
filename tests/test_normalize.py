import pytest

from pology.normalize import noinvisible


@pytest.mark.parametrize(
    "input,output",
    (
        ("\xa0", "\xa0"),
    )
)
def test_noinvisible(input, output):
    assert noinvisible(input) == output

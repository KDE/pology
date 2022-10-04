import pytest

from pology.colors import ColorString


class TTYMock:

    def isatty(self):
        return True


TTY_MOCK = TTYMock()


@pytest.mark.parametrize(
    "input,output,ctype,dest",
    (
        ("<red>foo</red>", "foo", None, None),
        ("<red>foo</red>", "foo", "term", None),
        ("<red>foo</red>", "\033[31mfoo\033[0;0m", "term", TTY_MOCK),
        ("<red>&lt;blue&gt;foo&lt;/blue&gt;</red>", "\033[31m<blue>foo</blue>\033[0;0m", "term", TTY_MOCK),
        ("<red>foo</red>", "<font color='#ff0000'>foo</font><br/>", "html", None),
    ),
)
def test_resolve(input, output, ctype, dest):
    assert ColorString(input).resolve(ctype=ctype, dest=dest) == output
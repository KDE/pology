from collections.abc import Hashable

from pology.message import Message


def test_hash():
    """Verify that we can create sets of messages."""
    message1 = Message({
        "source": [['some/path', 123]],
    })
    message2 = Message({
        "source": [['some/other/path', 456]],
    })
    _set = {message1, message1, message2}
    assert len(_set) == 2


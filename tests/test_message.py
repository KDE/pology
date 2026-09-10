from collections.abc import Hashable

from pology.message import Message, MessageUnsafe


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


def test_message_unsafe_flags():
    """Changing the fuzzy flag on MessageUnsafe works and keeps the flag order."""
    message = MessageUnsafe({"msgid": "Hello", "flag": ["c-format"]})
    message.fuzzy = True
    assert list(message.flag) == ["c-format", "fuzzy"]
    message.fuzzy = False
    assert list(message.flag) == ["c-format"]
    # Must not raise, as with Message.
    message.flag.remove("fuzzy")

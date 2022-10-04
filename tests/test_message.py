from collections.abc import Hashable

from pology.message import Message


def test_hashable():
    """Verify that we can create sets of messages."""
    {Message()}


from pology.monitored import Monitored


def test_getattr():
    monitored = Monitored()
    expected = object()
    assert getattr(monitored, "foo", expected) == expected

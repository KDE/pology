import os

from pology.catalog import Catalog
from pology.message import Message


TEMPLATE_FILEPATH = os.path.join(
    os.path.dirname(__file__), "files", "template.pot")


def test_template_load():
    catalog = Catalog(TEMPLATE_FILEPATH)
    message_iterator = iter(catalog)
    actual = list(message_iterator)
    expected = [
        Message({
            "source": [['some/path', 123]],
            "refline": 14,
            "refentry": 1,
            "msgid": "Source string",
            "msgstr": [""],
        })
    ]
    assert actual == expected

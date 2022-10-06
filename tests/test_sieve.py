import os
from unittest.mock import patch

import pytest

from pology.catalog import Catalog
from pology.colors import ColorString
from pology.message import Message
from pology.sieve.check_tp_kde import Sieve as CheckTpKDESieve


class SieveParams:
    check = None
    lokalize = False
    showmsg = False
    strict = False


SIEVE_PARAMS = SieveParams()


@pytest.mark.parametrize(
    "input,output",
    (
        ("&Პარამეტრი:", 'KDE4 markup: not well-formed (invalid token).'),
    ),
)
def test_check_tp_kde(input, output):
    catalog_file_path = (
        os.path.join(os.path.dirname(__file__), "files/template.pot")
    )
    with open(catalog_file_path, "rb") as catalog_input:
        catalog = Catalog("messages/aa/foo.po", readfh=catalog_input)
    sieve = CheckTpKDESieve(SIEVE_PARAMS)
    sieve.process_header(hdr=None, cat=catalog)
    message = Message({"msgstr": input})
    with patch('pology.sieve.check_tp_kde.report_on_msg_hl') as callee:
        sieve.process(message, cat=catalog)
        issues = [('msgstr', 0, [(0, 1, ColorString(output))])]
        callee.assert_called_once_with(issues, message, catalog)
    assert sieve.nproblems == 1
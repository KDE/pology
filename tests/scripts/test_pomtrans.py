try:
    from mock import MagicMock, patch
except ImportError:
    from unittest.mock import MagicMock, patch
import pytest

from scripts.pomtrans import Translator_apertium


@pytest.fixture(
    scope="module",
    params=[
        # Apertium 3.8.3
        (
            ["first example", "second example"],
            "first example<br>.second example",  # expected request
            "Primer ejemplo<br>.Segundo ejemplo",  # response
            ["Primer ejemplo", "Segundo ejemplo"],
        ),
    ],
)
def translation_workflow(request):
    yield request.param


@patch("scripts.pomtrans.collect_system")
@patch("scripts.pomtrans.subprocess.call")
def test_apertium_translation_workflow(
    subprocess_patch, collection_patch, translation_workflow
):
    (
        text,
        expected_translator_input,
        translator_output,
        expected_translation,
    ) = translation_workflow

    # patch two calls to 'collect_system':
    #  - the first call validates the language pair
    #  - the second call performs translations
    # each call returns stdout, stderr, and an exit code
    collection_patch.side_effect = [
        ("", "<stderr content>", 0),
        (translator_output, "", 0),
    ]

    options = MagicMock(
        data_directory=None,
        tmode=None,
        transerv_bin=None,
    )

    translator = Translator_apertium("eng", "spa", options=options)
    translation = translator.translate(text)

    setup_call, translation_call = collection_patch.call_args_list
    assert translation_call.kwargs["instr"] == expected_translator_input
    assert translation == expected_translation

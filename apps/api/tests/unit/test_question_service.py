import pytest

from uvts_api.services.questions import page_labelled_manual_text


def test_labels_manual_pages_without_dropping_blank_pages() -> None:
    assert page_labelled_manual_text(
        [
            {"page": 1, "text": "Start here."},
            {"page": 2, "text": ""},
            {"page": 3, "text": "Recovery steps."},
        ]
    ) == (
        "[Page 1]\nStart here.\n\n"
        "[Page 2]\n\n\n"
        "[Page 3]\nRecovery steps."
    )


@pytest.mark.parametrize(
    "pages",
    [
        [],
        [{"page": 0, "text": "Content"}],
        [{"page": 1, "text": 7}],
        [{"page": 1, "text": "   "}],
    ],
)
def test_rejects_invalid_or_unreadable_stored_pages(pages: list[dict[str, object]]) -> None:
    with pytest.raises(ValueError):
        page_labelled_manual_text(pages)

from pathlib import Path

import pytest

from tests.pdf_helpers import write_pdf
from uvts_api.services.documents import ManualValidationError, inspect_pdf


def test_extracts_text_with_page_provenance(tmp_path: Path) -> None:
    result = inspect_pdf(write_pdf(tmp_path / "manual.pdf", pages=2))

    assert result.page_count == 2
    assert result.pages == [
        {"page": 1, "text": "Readable page 1"},
        {"page": 2, "text": "Readable page 2"},
    ]


def test_preserves_blank_pages_and_their_page_numbers(tmp_path: Path) -> None:
    result = inspect_pdf(
        write_pdf(tmp_path / "manual-with-blank.pdf", pages=3, text_pages={1, 3})
    )

    assert result.pages == [
        {"page": 1, "text": "Readable page 1"},
        {"page": 2, "text": ""},
        {"page": 3, "text": "Readable page 3"},
    ]


@pytest.mark.parametrize(
    ("filename", "pages", "with_text", "encrypted", "code"),
    [
        ("empty.pdf", 0, False, False, "manual_page_count"),
        ("long.pdf", 21, True, False, "manual_page_limit"),
        ("scan.pdf", 1, False, False, "manual_no_readable_text"),
        ("locked.pdf", 1, True, True, "manual_password_protected"),
    ],
)
def test_rejects_unsupported_pdfs(
    tmp_path: Path,
    filename: str,
    pages: int,
    with_text: bool,
    encrypted: bool,
    code: str,
) -> None:
    path = write_pdf(
        tmp_path / filename,
        pages=pages,
        with_text=with_text,
        encrypted=encrypted,
    )

    with pytest.raises(ManualValidationError) as raised:
        inspect_pdf(path)

    assert raised.value.code == code

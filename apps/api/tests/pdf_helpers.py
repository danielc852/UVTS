from pathlib import Path

from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject


def write_pdf(
    path: Path,
    *,
    pages: int = 1,
    with_text: bool = True,
    text_pages: set[int] | None = None,
    encrypted: bool = False,
) -> Path:
    writer = PdfWriter()
    for page_number in range(1, pages + 1):
        page = writer.add_blank_page(width=612, height=792)
        if with_text and (text_pages is None or page_number in text_pages):
            font = DictionaryObject(
                {
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                }
            )
            font_reference = writer._add_object(font)  # noqa: SLF001 - test PDF builder
            page[NameObject("/Resources")] = DictionaryObject(
                {
                    NameObject("/Font"): DictionaryObject(
                        {NameObject("/F1"): font_reference}
                    )
                }
            )
            content = DecodedStreamObject()
            content.set_data(
                f"BT /F1 12 Tf 72 720 Td (Readable page {page_number}) Tj ET".encode()
            )
            page[NameObject("/Contents")] = writer._add_object(content)  # noqa: SLF001
    if encrypted:
        writer.encrypt("secret")
    with path.open("wb") as destination:
        writer.write(destination)
    return path

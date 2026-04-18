import csv
import io
import os

import fitz

SUPPORTED_TYPES = {".txt", ".pdf", ".csv"}

_EXTRACTORS: dict[str, callable] = {}


def _decode(content: bytes) -> str:
    try:
        return content.decode("utf-8")
    except UnicodeDecodeError:
        return content.decode("latin-1")


def _extract_txt(content: bytes) -> str:
    return _decode(content)


def _extract_pdf(content: bytes) -> str:
    with fitz.open(stream=content, filetype="pdf") as doc:
        text = "\n".join(page.get_text() for page in doc)
    import re
    # Rejoin words hyphenated across line-breaks (e.g. "sim-\nple" → "simple")
    text = re.sub(r"-\n(\S)", r"\1", text)
    # Collapse single newlines into spaces so text flows as prose.
    # RecursiveCharacterTextSplitter splits on \n preferentially; keeping layout
    # newlines makes overlap land on \n boundaries and shrinks effective overlap
    # to near-zero. Only true paragraph breaks (\n\n) are preserved.
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)
    return text


def _extract_csv(content: bytes) -> str:
    rows = list(csv.reader(io.StringIO(_decode(content))))
    if not rows:
        return ""
    return "\n".join(" | ".join(cell.strip() for cell in row) for row in rows)


_EXTRACTORS = {
    ".txt": _extract_txt,
    ".pdf": _extract_pdf,
    ".csv": _extract_csv,
}


def parse_file(filename: str, content: bytes) -> str:
    if not content:
        raise ValueError("Uploaded file is empty.")

    ext = os.path.splitext(filename)[-1].lower()
    extractor = _EXTRACTORS.get(ext)
    if extractor is None:
        raise ValueError(f"Unsupported file type '{ext}'. Supported: {', '.join(sorted(SUPPORTED_TYPES))}")

    text = extractor(content)
    if not text.strip():
        raise ValueError("No readable text found in the file.")
    return text

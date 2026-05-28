from pathlib import Path

from pypdf import PdfReader

MIN_EXTRACTED_TEXT_LENGTH = 30
UNREADABLE_PDF_MESSAGE = "텍스트를 추출할 수 없는 PDF입니다. 스캔본은 OCR 기능이 필요합니다."


def extract_text(file_path: str) -> str:
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Contract file not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".txt":
        text = _extract_txt_text(path)
    elif suffix == ".pdf":
        text = _extract_pdf_text(path)
    elif suffix in {".png", ".jpg", ".jpeg"}:
        raise ValueError("Image contract files are not supported yet. OCR support is required for image files.")
    else:
        raise ValueError("Only .txt and text-based .pdf contract files are supported.")

    if len(text.strip()) < MIN_EXTRACTED_TEXT_LENGTH:
        if suffix == ".pdf":
            raise ValueError(UNREADABLE_PDF_MESSAGE)
        raise ValueError("The contract text is empty or too short to index.")

    return text


def _extract_txt_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp949")


def _extract_pdf_text(path: Path) -> str:
    try:
        reader = PdfReader(str(path))
        page_texts = [page.extract_text() or "" for page in reader.pages]
    except Exception as exception:
        raise ValueError(UNREADABLE_PDF_MESSAGE) from exception

    return "\n\n".join(page_texts).strip()

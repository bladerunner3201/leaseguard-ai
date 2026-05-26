def chunk_text(text: str, chunk_size: int = 700, overlap: int = 80) -> list[str]:
    if not text:
        return []
    normalized_text = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    if not normalized_text:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(normalized_text):
        end = start + chunk_size
        chunks.append(normalized_text[start:end])
        next_start = end - overlap
        start = next_start if next_start > start else end
    return chunks

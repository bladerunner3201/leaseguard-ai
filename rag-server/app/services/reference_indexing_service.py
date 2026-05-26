import hashlib
from pathlib import Path

from app.services.chunking_service import chunk_text
from app.services.embedding_service import embed_texts
from app.vectorstore.chroma_client import get_legal_reference_collection


def index_references() -> dict:
    data_root = Path(__file__).resolve().parents[3] / "data"
    targets = [
        ("law", data_root / "legal_reference"),
        ("checklist", data_root / "checklist"),
    ]

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for source_type, directory in targets:
        if not directory.exists():
            continue

        for path in sorted(directory.glob("*.txt")):
            text = _read_text(path)
            chunks = chunk_text(text)
            title = path.stem.replace("_", " ")

            for chunk_index, chunk in enumerate(chunks):
                stable_key = f"{source_type}:{path.name}:{chunk_index}:{hashlib.sha1(chunk.encode('utf-8')).hexdigest()}"
                ids.append(hashlib.sha1(stable_key.encode("utf-8")).hexdigest())
                documents.append(chunk)
                metadatas.append(
                    {
                        "sourceType": source_type,
                        "title": title,
                        "fileName": path.name,
                        "chunkIndex": chunk_index,
                    }
                )

    if ids:
        collection = get_legal_reference_collection()
        collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embed_texts(documents),
        )

    return {
        "status": "INDEXED",
        "collection": "legal_reference",
        "indexedChunks": len(ids),
    }


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp949")

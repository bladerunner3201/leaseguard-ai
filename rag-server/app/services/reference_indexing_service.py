import json
import re
from pathlib import Path

from app.services.chunking_service import chunk_text
from app.services.embedding_service import embed_texts
from app.vectorstore.chroma_client import get_legal_reference_collection


def index_references() -> dict:
    repo_data_root = Path(__file__).resolve().parents[3] / "data"
    rag_data_root = Path(__file__).resolve().parents[2] / "data"
    curated_root = rag_data_root / "reference_sources" / "curated"
    manifest_path = rag_data_root / "reference_sources" / "source_manifest.json"
    manifest_by_file = _load_manifest_by_related_file(manifest_path)

    targets = [
        ("law", repo_data_root / "legal_reference", None),
        ("checklist", repo_data_root / "checklist", None),
        ("curated", curated_root, manifest_by_file),
    ]

    total_indexed_chunks = 0
    indexed_files = 0
    collection = get_legal_reference_collection()

    for default_source_type, directory, manifest in targets:
        if not directory.exists():
            continue

        for path in sorted(directory.glob("*.txt")):
            text = _read_text(path)
            parsed = _parse_curated_text(text) if default_source_type == "curated" else {}
            chunks = chunk_text(text)
            metadata_base = _build_metadata_base(path, default_source_type, parsed, manifest)

            ids: list[str] = []
            documents: list[str] = []
            metadatas: list[dict] = []

            for chunk_index, chunk in enumerate(chunks):
                ids.append(f"{metadata_base['sourceType']}:{path.name}:{chunk_index}")
                documents.append(chunk)
                metadatas.append(
                    {
                        **metadata_base,
                        "chunkIndex": chunk_index,
                    }
                )

            _delete_by_file_name(collection, path.name)

            if ids:
                collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                    embeddings=embed_texts(documents),
                )
                total_indexed_chunks += len(ids)
                indexed_files += 1

    return {
        "status": "INDEXED",
        "collection": "legal_reference",
        "indexedFiles": indexed_files,
        "indexedChunks": total_indexed_chunks,
    }


def _build_metadata_base(path: Path, default_source_type: str, parsed: dict, manifest: dict | None) -> dict:
    manifest_items = manifest.get(path.name, []) if manifest else []
    manifest_titles = [item.get("title", "") for item in manifest_items if item.get("title")]
    publishers = [item.get("publisher", "") for item in manifest_items if item.get("publisher")]
    urls = [item.get("url", "") for item in manifest_items if item.get("url")]

    return {
        "category": parsed.get("category") or _category_from_file_name(path.name),
        "sourceType": parsed.get("source_type") or _manifest_source_type(manifest_items) or default_source_type,
        "title": parsed.get("title") or _manifest_title(manifest_items) or path.stem.replace("_", " "),
        "fileName": path.name,
        "keywords": parsed.get("keywords") or "",
        "manifestTitle": " | ".join(manifest_titles),
        "relatedSourceTitles": " | ".join(manifest_titles),
        "publisher": " | ".join(dict.fromkeys(publishers)),
        "url": " | ".join(dict.fromkeys(urls)),
    }


def _parse_curated_text(text: str) -> dict:
    sections: dict[str, str] = {}
    current_key: str | None = None
    current_lines: list[str] = []

    for line in text.splitlines():
        match = re.fullmatch(r"\[([A-Za-z0-9_ -]+)\]", line.strip())
        if match:
            if current_key:
                sections[current_key] = "\n".join(current_lines).strip()
            current_key = match.group(1).strip().lower()
            current_lines = []
            continue

        if current_key:
            current_lines.append(line)

    if current_key:
        sections[current_key] = "\n".join(current_lines).strip()

    if "keywords" in sections:
        sections["keywords"] = _normalize_keywords(sections["keywords"])

    return sections


def _normalize_keywords(value: str) -> str:
    return ", ".join(
        keyword.strip("- ").strip()
        for keyword in re.split(r"[,\n]", value)
        if keyword.strip("- ").strip()
    )


def _load_manifest_by_related_file(path: Path) -> dict[str, list[dict]]:
    if not path.exists():
        return {}

    items = json.loads(path.read_text(encoding="utf-8"))
    by_file: dict[str, list[dict]] = {}
    for item in items:
        for related_file in item.get("relatedFiles", []):
            by_file.setdefault(related_file, []).append(item)
    return by_file


def _manifest_source_type(items: list[dict]) -> str:
    source_types = [item.get("sourceType", "") for item in items if item.get("sourceType")]
    return " + ".join(dict.fromkeys(source_types))


def _manifest_title(items: list[dict]) -> str:
    titles = [item.get("title", "") for item in items if item.get("title")]
    return titles[0] if titles else ""


def _category_from_file_name(file_name: str) -> str:
    return file_name.removesuffix(".txt")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp949")


def _delete_by_file_name(collection, file_name: str) -> None:
    try:
        collection.delete(where={"fileName": file_name})
    except Exception:
        pass

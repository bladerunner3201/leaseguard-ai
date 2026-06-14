from app.schemas.chat_schema import RagSource
from app.services.embedding_service import embed_text
from app.vectorstore.chroma_client import get_legal_reference_collection, get_user_contracts_collection

CATEGORY_EXPANSIONS = [
    {
        "category": "deposit_return",
        "triggers": ["보증금", "반환", "돌려받", "refund", "deposit", "return"],
        "expansion": "deposit_return 보증금 반환 반환 지연 임대차 보증금 security deposit refund return delay tenant protection",
    },
    {
        "category": "special_clause_repair",
        "triggers": ["특약", "불리", "수리", "수리비", "원상복구", "원상회복", "special", "clause", "repair", "restoration"],
        "expansion": "special_clause_repair 특약 불리한 조항 수리비 원상복구 임차인 부담 unfair term repair cost restoration tenant burden",
    },
    {
        "category": "move_in_fixed_date",
        "triggers": ["전입", "전입신고", "확정일자", "대항력", "우선변제권", "move in", "fixed date", "priority repayment"],
        "expansion": "move_in_fixed_date 전입신고 확정일자 대항력 우선변제권 resident registration fixed date opposing power priority repayment",
    },
    {
        "category": "registry_check",
        "triggers": ["등기부", "근저당", "압류", "선순위", "registry", "mortgage", "seizure", "senior lien"],
        "expansion": "registry_check 등기부등본 근저당 압류 선순위 권리 소유자 임대인 registry mortgage seizure senior rights ownership lessor encumbrance",
    },
    {
        "category": "jeonse_fraud_prevention",
        "triggers": ["전세사기", "보증보험", "시세", "jeonse fraud", "insurance", "market price"],
        "expansion": "jeonse_fraud_prevention 전세사기 예방 보증보험 시세 체크리스트 fraud prevention guarantee insurance market price checklist",
    },
    {
        "category": "standard_contract",
        "triggers": ["표준계약", "빠진", "누락", "standard contract", "missing"],
        "expansion": "standard_contract 표준 임대차계약서 누락 항목 필수 조항 standard lease contract missing items required clauses checklist",
    },
]

NORMALIZED_SOURCE_TYPES = {
    "contract",
    "law",
    "checklist",
    "guide",
    "legal_reference",
    "standard_contract",
}

HYBRID_KEYWORD_WEIGHT = 0.35
HYBRID_METADATA_WEIGHT = 1.0


def retrieve_sources(
    message: str,
    anonymous_session_id: str,
    contract_id: int | None,
    rewritten_query: str | None = None,
) -> list[RagSource]:
    query_text = rewritten_query or message
    category_signal = f"{message} {query_text}"
    expected_categories = _infer_expected_categories(category_signal)
    expanded_query = _expand_query(query_text, expected_categories)
    query_embedding = embed_text(expanded_query)

    contract_sources = _query_user_contracts(query_embedding, query_text, anonymous_session_id, contract_id)
    reference_sources = _query_legal_references(query_embedding, category_signal, expected_categories)
    return _deduplicate_sources(contract_sources + reference_sources)


def _query_user_contracts(
    query_embedding: list[float],
    query_text: str,
    anonymous_session_id: str,
    contract_id: int | None,
) -> list[RagSource]:
    where = {"anonymousSessionId": anonymous_session_id}
    if contract_id is not None:
        where = {
            "$and": [
                {"anonymousSessionId": anonymous_session_id},
                {"contractId": contract_id},
            ]
        }

    return _query_collection(
        collection=get_user_contracts_collection(),
        query_text=query_text,
        query_embedding=query_embedding,
        where=where,
        n_results=4,
        source_type_fallback="contract",
        limit=3,
    )


def _query_legal_references(
    query_embedding: list[float],
    message: str,
    expected_categories: list[str],
) -> list[RagSource]:
    return _query_collection(
        collection=get_legal_reference_collection(),
        query_text=message,
        query_embedding=query_embedding,
        where=None,
        n_results=14,
        source_type_fallback="legal_reference",
        message=message,
        expected_categories=expected_categories,
        limit=7,
    )


def _query_collection(
    collection,
    query_text: str,
    query_embedding: list[float],
    where: dict | None,
    n_results: int,
    source_type_fallback: str,
    message: str = "",
    expected_categories: list[str] | None = None,
    limit: int | None = None,
) -> list[RagSource]:
    query_text = query_text or message
    try:
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exception:
        print(f"[rag-chat] ChromaDB retrieval failed: {type(exception).__name__}: {exception}")
        return []

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]
    ids = result.get("ids", [[]])[0]

    ranked_by_id = {}
    for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        metadata = metadata or {}
        similarity = _distance_to_similarity(distance)
        metadata_bonus = _metadata_bonus(metadata, message, expected_categories or [])
        keyword_score = _keyword_score(query_text, document or "", metadata)
        ranked_by_id[item_id] = {
            "document": document or "",
            "metadata": metadata,
            "similarity": similarity,
            "score": (similarity or 0.0) + (metadata_bonus * HYBRID_METADATA_WEIGHT) + (keyword_score * HYBRID_KEYWORD_WEIGHT),
        }

    for item_id, document, metadata in _keyword_candidates(collection, where):
        if item_id in ranked_by_id:
            continue
        metadata = metadata or {}
        keyword_score = _keyword_score(query_text, document or "", metadata)
        if keyword_score <= 0:
            continue
        metadata_bonus = _metadata_bonus(metadata, message, expected_categories or [])
        ranked_by_id[item_id] = {
            "document": document or "",
            "metadata": metadata,
            "similarity": round(keyword_score, 4),
            "score": (keyword_score * HYBRID_KEYWORD_WEIGHT) + (metadata_bonus * HYBRID_METADATA_WEIGHT),
        }

    ranked_rows = list(ranked_by_id.values())

    ranked_rows.sort(key=lambda row: row["score"], reverse=True)
    if limit is not None:
        ranked_rows = _select_diverse_rows(ranked_rows, limit)

    sources: list[RagSource] = []
    for row in ranked_rows:
        metadata = row["metadata"]
        sources.append(
            RagSource(
                sourceType=_normalize_source_type(metadata.get("sourceType"), source_type_fallback),
                sourceTitle=metadata.get("documentName") or metadata.get("title") or metadata.get("fileName") or "unknown",
                pageNumber=None,
                chunkText=row["document"] or "",
                similarityScore=row["similarity"],
            )
        )
    return sources


def _select_diverse_rows(rows: list[dict], limit: int) -> list[dict]:
    selected: list[dict] = []
    deferred: list[dict] = []
    title_counts: dict[tuple[str, str], int] = {}

    for row in rows:
        metadata = row.get("metadata", {})
        source_type = _normalize_source_type(metadata.get("sourceType"), "legal_reference")
        title = metadata.get("documentName") or metadata.get("title") or metadata.get("fileName") or "unknown"
        key = (source_type, title)
        max_per_title = 1 if source_type != "contract" else 3

        if title_counts.get(key, 0) < max_per_title:
            selected.append(row)
            title_counts[key] = title_counts.get(key, 0) + 1
        else:
            deferred.append(row)

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        selected.extend(deferred[: limit - len(selected)])

    return selected


def _keyword_candidates(collection, where: dict | None) -> list[tuple[str, str, dict]]:
    try:
        result = collection.get(
            where=where,
            include=["documents", "metadatas"],
            limit=250,
        )
    except TypeError:
        try:
            result = collection.get(
                include=["documents", "metadatas"],
                limit=250,
            )
        except Exception:
            return []
    except Exception:
        return []

    ids = result.get("ids", [])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])
    return list(zip(ids, documents, metadatas))


def _normalize_source_type(value: str | None, fallback: str) -> str:
    normalized = (value or fallback or "legal_reference").strip().lower().replace(" ", "_")
    if normalized == "curated":
        return "legal_reference"
    if normalized in NORMALIZED_SOURCE_TYPES:
        return normalized
    for candidate in ["standard_contract", "checklist", "guide", "law", "legal_reference", "contract"]:
        if candidate in normalized:
            return candidate
    return fallback if fallback in NORMALIZED_SOURCE_TYPES else "legal_reference"


def _distance_to_similarity(distance: float | None) -> float | None:
    if distance is None:
        return None
    return round(max(0.0, min(1.0, 1.0 - float(distance))), 4)


def _infer_expected_categories(message: str) -> list[str]:
    normalized = message.lower()
    categories: list[str] = []
    for rule in CATEGORY_EXPANSIONS:
        if any(trigger in normalized for trigger in rule["triggers"]):
            categories.append(rule["category"])
    return categories


def _expand_query(message: str, expected_categories: list[str]) -> str:
    expansions = [
        rule["expansion"]
        for rule in CATEGORY_EXPANSIONS
        if rule["category"] in expected_categories
    ]
    if not expansions:
        return message
    return f"{message} {' '.join(expansions)}"


def _metadata_bonus(metadata: dict, message: str, expected_categories: list[str]) -> float:
    if not metadata:
        return 0.0

    searchable_metadata = " ".join(
        str(metadata.get(key, ""))
        for key in ["category", "title", "fileName", "keywords", "manifestTitle", "relatedSourceTitles"]
    ).lower()

    bonus = 0.0
    for category in expected_categories:
        if category in searchable_metadata:
            bonus += 0.4

    normalized_message = message.lower()
    for rule in CATEGORY_EXPANSIONS:
        if rule["category"] not in expected_categories:
            continue
        matched_triggers = sum(
            1
            for trigger in rule["triggers"]
            if trigger in normalized_message and trigger in searchable_metadata
        )
        bonus += min(0.25, matched_triggers * 0.05)

    return bonus


def _keyword_score(query: str, document: str, metadata: dict) -> float:
    query_tokens = _tokenize_for_keyword(query)
    if not query_tokens:
        return 0.0

    searchable_text = " ".join(
        [
            document or "",
            str(metadata.get("category", "")),
            str(metadata.get("title", "")),
            str(metadata.get("fileName", "")),
            str(metadata.get("keywords", "")),
            str(metadata.get("manifestTitle", "")),
            str(metadata.get("relatedSourceTitles", "")),
        ]
    ).lower()
    doc_tokens = set(_tokenize_for_keyword(searchable_text))
    if not doc_tokens:
        return 0.0

    matched = sum(1 for token in query_tokens if token in doc_tokens or token in searchable_text)
    coverage = matched / max(1, len(set(query_tokens)))
    return min(1.0, coverage)


def _tokenize_for_keyword(value: str) -> list[str]:
    raw_tokens = [token.lower() for token in value.replace("_", " ").split()]
    tokens: list[str] = []
    for token in raw_tokens:
        cleaned = "".join(ch for ch in token if ch.isalnum() or "\uac00" <= ch <= "\ud7a3")
        if len(cleaned) >= 2:
            tokens.append(cleaned)
    return tokens


def _deduplicate_sources(sources: list[RagSource]) -> list[RagSource]:
    deduplicated: list[RagSource] = []
    seen: set[tuple[str, str, str]] = set()

    for source in sources:
        key = (source.sourceType, source.sourceTitle, source.chunkText[:160])
        if key in seen:
            continue
        seen.add(key)
        deduplicated.append(source)

    return deduplicated

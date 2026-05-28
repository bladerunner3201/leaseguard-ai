from app.schemas.chat_schema import RagSource
from app.services.embedding_service import embed_text
from app.vectorstore.chroma_client import get_legal_reference_collection, get_user_contracts_collection

CATEGORY_EXPANSIONS = [
    {
        "category": "deposit_return",
        "triggers": ["보증금", "반환", "돌려받", "refund", "deposit", "return"],
        "expansion": "deposit_return security deposit refund return delay lease deposit tenant protection",
    },
    {
        "category": "special_clause_repair",
        "triggers": ["특약", "불리", "수리", "수리비", "원상복구", "원상회복", "special", "clause", "repair", "restoration"],
        "expansion": "special_clause_repair special clause unfair term repair cost restoration tenant burden",
    },
    {
        "category": "move_in_fixed_date",
        "triggers": ["전입", "전입신고", "확정일자", "대항력", "우선변제권", "move in", "fixed date", "priority repayment"],
        "expansion": "move_in_fixed_date resident registration fixed date opposing power priority repayment",
    },
    {
        "category": "registry_check",
        "triggers": ["등기부", "근저당", "압류", "선순위", "registry", "mortgage", "seizure", "senior lien"],
        "expansion": "registry_check registry mortgage seizure senior rights ownership lessor encumbrance",
    },
    {
        "category": "jeonse_fraud_prevention",
        "triggers": ["전세사기", "보증보험", "시세", "jeonse fraud", "insurance", "market price"],
        "expansion": "jeonse_fraud_prevention fraud prevention guarantee insurance market price checklist",
    },
    {
        "category": "standard_contract",
        "triggers": ["표준계약", "빠진", "누락", "standard contract", "missing"],
        "expansion": "standard_contract standard lease contract missing items required clauses checklist",
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
    sources: list[RagSource] = []

    sources.extend(_query_user_contracts(query_embedding, anonymous_session_id, contract_id))
    sources.extend(_query_legal_references(query_embedding, message, expected_categories))

    return sources


def _query_user_contracts(
    query_embedding: list[float],
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
        query_embedding=query_embedding,
        where=where,
        n_results=3,
        source_type_fallback="contract",
    )


def _query_legal_references(
    query_embedding: list[float],
    message: str,
    expected_categories: list[str],
) -> list[RagSource]:
    return _query_collection(
        collection=get_legal_reference_collection(),
        query_embedding=query_embedding,
        where=None,
        n_results=12,
        source_type_fallback="legal_reference",
        message=message,
        expected_categories=expected_categories,
        limit=7,
    )


def _query_collection(
    collection,
    query_embedding: list[float],
    where: dict | None,
    n_results: int,
    source_type_fallback: str,
    message: str = "",
    expected_categories: list[str] | None = None,
    limit: int | None = None,
) -> list[RagSource]:
    try:
        result = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return []

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    ranked_rows = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        similarity = _distance_to_similarity(distance)
        rerank_score = (similarity or 0.0) + _metadata_bonus(metadata, message, expected_categories or [])
        ranked_rows.append(
            {
                "document": document,
                "metadata": metadata,
                "similarity": similarity,
                "score": rerank_score,
            }
        )

    ranked_rows.sort(key=lambda row: row["score"], reverse=True)
    if limit is not None:
        ranked_rows = ranked_rows[:limit]

    sources: list[RagSource] = []
    for row in ranked_rows:
        metadata = row["metadata"]
        sources.append(
            RagSource(
                sourceType=_normalize_source_type(metadata.get("sourceType"), source_type_fallback),
                sourceTitle=metadata.get("documentName") or metadata.get("title") or metadata.get("fileName") or "unknown",
                pageNumber=None,
                chunkText=row["document"],
                similarityScore=row["similarity"],
            )
        )
    return sources


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
            bonus += 0.35

    normalized_message = message.lower()
    for rule in CATEGORY_EXPANSIONS:
        if rule["category"] not in expected_categories:
            continue
        matched_triggers = sum(1 for trigger in rule["triggers"] if trigger in normalized_message and trigger in searchable_metadata)
        bonus += min(0.2, matched_triggers * 0.05)

    return bonus

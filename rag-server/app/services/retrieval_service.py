from app.schemas.chat_schema import RagSource
from app.services.embedding_service import embed_text
from app.vectorstore.chroma_client import get_legal_reference_collection, get_user_contracts_collection


def retrieve_sources(message: str, anonymous_session_id: str, contract_id: int | None) -> list[RagSource]:
    query_embedding = embed_text(message)
    sources: list[RagSource] = []

    sources.extend(_query_user_contracts(query_embedding, anonymous_session_id, contract_id))
    sources.extend(_query_legal_references(query_embedding))

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
        n_results=4,
        source_type_fallback="contract",
    )


def _query_legal_references(query_embedding: list[float]) -> list[RagSource]:
    return _query_collection(
        collection=get_legal_reference_collection(),
        query_embedding=query_embedding,
        where=None,
        n_results=4,
        source_type_fallback="legal_reference",
    )


def _query_collection(
    collection,
    query_embedding: list[float],
    where: dict | None,
    n_results: int,
    source_type_fallback: str,
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

    sources: list[RagSource] = []
    for document, metadata, distance in zip(documents, metadatas, distances):
        metadata = metadata or {}
        sources.append(
            RagSource(
                sourceType=metadata.get("sourceType", source_type_fallback),
                sourceTitle=metadata.get("documentName") or metadata.get("title") or metadata.get("fileName") or "unknown",
                pageNumber=None,
                chunkText=document,
                similarityScore=_distance_to_similarity(distance),
            )
        )
    return sources


def _distance_to_similarity(distance: float | None) -> float | None:
    if distance is None:
        return None
    return round(max(0.0, min(1.0, 1.0 - float(distance))), 4)

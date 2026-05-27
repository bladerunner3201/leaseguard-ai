from app.schemas.contract_schema import ContractIndexRequest, ContractIndexResponse
from app.services.chunking_service import chunk_text
from app.services.contract_parser import extract_text
from app.services.embedding_service import embed_texts
from app.services.risk_analysis_service import analyze_contract
from app.vectorstore.chroma_client import get_user_contracts_collection


def index_contract(request: ContractIndexRequest) -> ContractIndexResponse:
    text = extract_text(request.filePath)
    chunks = chunk_text(text)

    ids: list[str] = []
    metadatas: list[dict] = []

    for chunk_index, chunk in enumerate(chunks):
        ids.append(f"contract:{request.anonymousSessionId}:{request.contractId}:{chunk_index}")
        metadatas.append(
            {
                "sourceType": "contract",
                "anonymousSessionId": request.anonymousSessionId,
                "contractId": request.contractId,
                "documentName": request.originalFileName,
                "chunkIndex": chunk_index,
            }
        )

    collection = get_user_contracts_collection()
    _delete_existing_contract_chunks(collection, request.anonymousSessionId, request.contractId)

    if ids:
        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
            embeddings=embed_texts(chunks),
        )

    return ContractIndexResponse(
        contractId=request.contractId,
        status="INDEXED",
        analysis=analyze_contract(text),
    )


def _delete_existing_contract_chunks(collection, anonymous_session_id: str, contract_id: int) -> None:
    try:
        collection.delete(
            where={
                "$and": [
                    {"anonymousSessionId": anonymous_session_id},
                    {"contractId": contract_id},
                ]
            }
        )
    except Exception:
        pass

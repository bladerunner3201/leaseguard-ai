import hashlib

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
        stable_key = (
            f"contract:{request.anonymousSessionId}:{request.contractId}:"
            f"{chunk_index}:{hashlib.sha1(chunk.encode('utf-8')).hexdigest()}"
        )
        ids.append(hashlib.sha1(stable_key.encode("utf-8")).hexdigest())
        metadatas.append(
            {
                "sourceType": "contract",
                "anonymousSessionId": request.anonymousSessionId,
                "contractId": request.contractId,
                "documentName": request.originalFileName,
                "chunkIndex": chunk_index,
            }
        )

    if ids:
        collection = get_user_contracts_collection()
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

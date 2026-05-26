import os

import chromadb
from chromadb.config import Settings

LEGAL_REFERENCE_COLLECTION = "legal_reference"
USER_CONTRACTS_COLLECTION = "user_contracts"


def get_chroma_client() -> chromadb.HttpClient:
    host = os.getenv("CHROMA_HOST", "localhost")
    port = int(os.getenv("CHROMA_PORT", "8001"))
    return chromadb.HttpClient(
        host=host,
        port=port,
        settings=Settings(anonymized_telemetry=False),
    )


def get_legal_reference_collection():
    return get_chroma_client().get_or_create_collection(
        name=LEGAL_REFERENCE_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )


def get_user_contracts_collection():
    return get_chroma_client().get_or_create_collection(
        name=USER_CONTRACTS_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

from fastapi import APIRouter

from app.services.reference_indexing_service import index_references

router = APIRouter(prefix="/rag/references", tags=["references"])


@router.post("/index")
def index_legal_references() -> dict:
    return index_references()

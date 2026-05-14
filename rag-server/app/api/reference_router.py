from fastapi import APIRouter

router = APIRouter(prefix="/rag/references", tags=["references"])


@router.post("/index")
def index_references() -> dict[str, str]:
    return {"status": "READY_TO_IMPLEMENT"}

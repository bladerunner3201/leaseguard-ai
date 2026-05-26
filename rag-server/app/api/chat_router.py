from fastapi import APIRouter

from app.schemas.chat_schema import RagChatRequest, RagChatResponse
from app.services.llm_service import generate_answer
from app.services.retrieval_service import retrieve_sources

router = APIRouter(prefix="/rag", tags=["chat"])


@router.post("/chat", response_model=RagChatResponse)
def chat(request: RagChatRequest) -> RagChatResponse:
    sources = retrieve_sources(
        message=request.message,
        anonymous_session_id=request.anonymousSessionId,
        contract_id=request.contractId,
    )

    return RagChatResponse(
        answer=generate_answer(request.message, sources),
        sources=sources,
    )

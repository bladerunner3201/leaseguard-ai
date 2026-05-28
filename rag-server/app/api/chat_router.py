from fastapi import APIRouter

from app.schemas.chat_schema import RagChatRequest, RagChatResponse
from app.services.llm_service import generate_answer
from app.services.retrieval_service import retrieve_sources

router = APIRouter(prefix="/rag", tags=["chat"])


@router.post("/chat", response_model=RagChatResponse)
def chat(request: RagChatRequest) -> RagChatResponse:
    chat_history = request.chatHistory or request.history
    retrieval_query = _build_retrieval_query(request.message, chat_history)
    sources = retrieve_sources(
        message=retrieval_query,
        anonymous_session_id=request.anonymousSessionId,
        contract_id=request.contractId,
    )

    return RagChatResponse(
        answer=generate_answer(request.message, sources, chat_history),
        sources=sources,
    )


def _build_retrieval_query(message: str, chat_history) -> str:
    normalized = (message or "").strip()
    if len(normalized) > 12 and not _looks_context_dependent(normalized):
        return normalized

    recent_user_messages = [
        history.content
        for history in chat_history
        if history.role == "user" and history.content
    ]
    if not recent_user_messages:
        return normalized
    return f"{recent_user_messages[-1]} {normalized}".strip()


def _looks_context_dependent(message: str) -> bool:
    markers = [
        "그럼",
        "방금",
        "그 부분",
        "그 조항",
        "그건",
        "그거",
        "이 부분",
        "이 조항",
        "어떻게 고쳐",
        "어떻게 물어",
    ]
    return any(marker in message for marker in markers)

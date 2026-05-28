from fastapi import APIRouter

from app.schemas.chat_schema import RagChatRequest, RagChatResponse
from app.services.llm_service import (
    detect_follow_up,
    detect_response_mode,
    generate_answer,
    rewrite_retrieval_query,
)
from app.services.retrieval_service import retrieve_sources

router = APIRouter(prefix="/rag", tags=["chat"])


@router.post("/chat", response_model=RagChatResponse)
def chat(request: RagChatRequest) -> RagChatResponse:
    chat_history = request.chatHistory or request.history
    response_mode = detect_response_mode(request.message)
    is_follow_up = detect_follow_up(request.message)
    rewritten_query = rewrite_retrieval_query(
        message=request.message,
        chat_history=chat_history,
        response_mode=response_mode,
        is_follow_up=is_follow_up,
    )
    print(
        "[rag-chat]",
        {
            "originalMessage": request.message[:160],
            "responseMode": response_mode,
            "isFollowUp": is_follow_up,
            "rewrittenQuery": rewritten_query[:500],
        },
    )

    sources = retrieve_sources(
        message=request.message,
        rewritten_query=rewritten_query,
        anonymous_session_id=request.anonymousSessionId,
        contract_id=request.contractId,
    )

    return RagChatResponse(
        answer=generate_answer(
            message=request.message,
            sources=sources,
            chat_history=chat_history,
            rewritten_query=rewritten_query,
            response_mode=response_mode,
            is_follow_up=is_follow_up,
        ),
        sources=sources,
    )

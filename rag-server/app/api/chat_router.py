from fastapi import APIRouter

from app.schemas.chat_schema import RagChatRequest, RagChatResponse
from app.services.chat_mode_service import detect_chat_intent
from app.services.llm_service import generate_answer, rewrite_retrieval_query
from app.services.retrieval_service import retrieve_sources

router = APIRouter(prefix="/rag", tags=["chat"])


@router.post("/chat", response_model=RagChatResponse)
def chat(request: RagChatRequest) -> RagChatResponse:
    chat_history = request.chatHistory or request.history
    chat_intent = detect_chat_intent(request.message)
    rewritten_query = rewrite_retrieval_query(
        message=request.message,
        chat_history=chat_history,
        chat_intent=chat_intent,
    )
    print(
        "[rag-chat]",
        {
            "originalMessage": request.message[:160],
            "topic": chat_intent.topic,
            "answerStyle": chat_intent.answerStyle,
            "safetyLevel": chat_intent.safetyLevel,
            "isFollowUp": chat_intent.isFollowUp,
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
            chat_intent=chat_intent,
        ),
        sources=sources,
    )

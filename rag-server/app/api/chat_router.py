from fastapi import APIRouter

from app.schemas.chat_schema import RagChatRequest, RagChatResponse

router = APIRouter(prefix="/rag", tags=["chat"])


@router.post("/chat", response_model=RagChatResponse)
def chat(request: RagChatRequest) -> RagChatResponse:
    return RagChatResponse(
        answer="RAG 채팅 기능 구현 전 기본 응답입니다.",
        sources=[],
    )

from fastapi import APIRouter

from app.schemas.chat_schema import RagChatRequest, RagChatResponse, RagSource

router = APIRouter(prefix="/rag", tags=["chat"])


@router.post("/chat", response_model=RagChatResponse)
def chat(request: RagChatRequest) -> RagChatResponse:
    return RagChatResponse(
        answer=(
            "This is a fixed stub answer for Spring Boot integration testing. "
            "The user message was received successfully. "
            "No real RAG search, legal review, OpenAI call, or ChromaDB lookup is performed at this stage."
        ),
        sources=[
            RagSource(
                sourceType="contract",
                sourceTitle="stub-contract-source",
                pageNumber=1,
                chunkText="Sample contract text: the deposit is returned after the lease ends.",
                similarityScore=0.91,
            ),
            RagSource(
                sourceType="checklist",
                sourceTitle="stub-lease-checklist",
                pageNumber=None,
                chunkText="Sample checklist text: review deposit return terms and special clauses before signing.",
                similarityScore=0.84,
            ),
        ],
    )

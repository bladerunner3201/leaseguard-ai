from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: str
    content: str


class RagChatRequest(BaseModel):
    anonymousSessionId: str
    contractId: int | None = None
    message: str
    chatHistory: list[ChatHistoryMessage] = Field(default_factory=list)
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class RagSource(BaseModel):
    sourceType: str
    sourceTitle: str
    pageNumber: int | None = None
    chunkText: str
    similarityScore: float | None = None


class RagChatResponse(BaseModel):
    answer: str
    sources: list[RagSource]

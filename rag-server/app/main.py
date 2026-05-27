from fastapi import FastAPI
from dotenv import load_dotenv

from app.api import chat_router, contract_router, reference_router

load_dotenv()

app = FastAPI(
    title="LeaseGuard AI RAG Server",
    description="ChromaDB retrieval MVP with optional OpenAI Chat API answer generation. LangChain is not used.",
)

app.include_router(reference_router.router)
app.include_router(contract_router.router)
app.include_router(chat_router.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "mode": "chroma-retrieval"}

from fastapi import FastAPI

from app.api import chat_router, contract_router, reference_router

app = FastAPI(title="LeaseGuard AI RAG Server")

app.include_router(reference_router.router)
app.include_router(contract_router.router)
app.include_router(chat_router.router)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}

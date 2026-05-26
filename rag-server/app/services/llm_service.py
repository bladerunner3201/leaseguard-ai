from app.schemas.chat_schema import RagSource


def generate_answer(message: str, sources: list[RagSource]) -> str:
    contract_count = sum(1 for source in sources if source.sourceType == "contract")
    reference_count = len(sources) - contract_count

    if not sources:
        return (
            "No matching ChromaDB chunks were found for this question. "
            "The contract may need to be indexed first, or the reference collection may be empty."
        )

    return (
        "ChromaDB retrieval completed without an LLM call. "
        f"Found {contract_count} contract chunk(s) and {reference_count} reference chunk(s). "
        "Review the returned sources for the retrieved context."
    )

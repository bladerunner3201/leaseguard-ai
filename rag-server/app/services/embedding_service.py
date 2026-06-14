import hashlib
import math
import os
import re

from openai import OpenAI
from dotenv import load_dotenv

LOCAL_VECTOR_SIZE = 128
DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
DEFAULT_EMBEDDING_DIMENSIONS = 128

load_dotenv()


def embed_texts(texts: list[str]) -> list[list[float]]:
    clean_texts = [text or "" for text in texts]
    if _should_use_openai_embeddings():
        try:
            return _embed_texts_with_openai(clean_texts)
        except Exception as exception:
            print(f"[embedding] OpenAI embedding failed, falling back to local hash: {type(exception).__name__}: {exception}")
    return [_embed_text_locally(text) for text in clean_texts]


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]


def get_embedding_provider_name() -> str:
    if _should_use_openai_embeddings():
        return "openai"
    return "local_hash"


def _should_use_openai_embeddings() -> bool:
    provider = os.getenv("EMBEDDING_PROVIDER", "auto").strip().lower()
    if provider == "local":
        return False
    if provider == "openai":
        return bool(os.getenv("OPENAI_API_KEY"))
    return bool(os.getenv("OPENAI_API_KEY"))


def _embed_texts_with_openai(texts: list[str]) -> list[list[float]]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model = os.getenv("OPENAI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL)
    dimensions = int(os.getenv("OPENAI_EMBEDDING_DIMENSIONS", str(DEFAULT_EMBEDDING_DIMENSIONS)))
    response = client.embeddings.create(
        model=model,
        input=texts,
        dimensions=dimensions,
    )
    return [item.embedding for item in response.data]


def _embed_text_locally(text: str) -> list[float]:
    vector = [0.0] * LOCAL_VECTOR_SIZE
    tokens = re.findall(r"\w+", text.lower())

    for token in tokens:
        for feature in _token_features(token):
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % LOCAL_VECTOR_SIZE
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _token_features(token: str) -> list[str]:
    features = [token]
    for size in range(2, 5):
        if len(token) >= size:
            features.extend(token[index : index + size] for index in range(len(token) - size + 1))
    return features

import hashlib
import math
import re

VECTOR_SIZE = 128


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [embed_text(text) for text in texts]


def embed_text(text: str) -> list[float]:
    vector = [0.0] * VECTOR_SIZE
    tokens = re.findall(r"\w+", text.lower())

    for token in tokens:
        for feature in _token_features(token):
            digest = hashlib.sha256(feature.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % VECTOR_SIZE
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

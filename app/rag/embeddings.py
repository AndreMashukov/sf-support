from typing import Literal

import httpx

from app.settings import settings

EmbeddingRole = Literal["passage", "query"]


def embeddings_configured() -> bool:
    key = settings.openrouter_api_key.strip()
    if not key or key.startswith("your-"):
        return False
    return True


def format_e5_input(text: str, role: EmbeddingRole) -> str:
    trimmed = text.lstrip()
    if trimmed.lower().startswith("query:") or trimmed.lower().startswith("passage:"):
        return text
    return f"{role}: {text}"


def embed_texts(
    texts: list[str],
    *,
    role: EmbeddingRole = "passage",
) -> list[list[float]]:
    if not texts:
        return []
    if not embeddings_configured():
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    model = settings.openrouter_embedding_model
    payload_input = (
        [format_e5_input(text, role) for text in texts]
        if "e5" in model.lower()
        else texts
    )
    response = httpx.post(
        settings.openrouter_embeddings_url,
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        },
        json={"model": model, "input": payload_input},
        timeout=60.0,
    )
    if response.status_code >= 400:
        raise RuntimeError(
            f"OpenRouter embeddings failed ({response.status_code}): {response.text}"
        )
    data = response.json().get("data")
    if not isinstance(data, list):
        raise RuntimeError("OpenRouter embeddings response had no data list")
    ordered = sorted(
        data,
        key=lambda row: row.get("index", 0) if isinstance(row, dict) else 0,
    )
    vectors: list[list[float]] = []
    for row in ordered:
        if not isinstance(row, dict) or not isinstance(row.get("embedding"), list):
            raise RuntimeError("OpenRouter embeddings response had a malformed vector")
        vectors.append([float(value) for value in row["embedding"]])
    if len(vectors) != len(texts):
        raise RuntimeError("OpenRouter embeddings count did not match input count")
    return vectors


def embed_text(text: str, *, role: EmbeddingRole = "passage") -> list[float]:
    return embed_texts([text], role=role)[0]

import hashlib
from pathlib import Path

# Match StudyForge platform-knowledge chunkText (characters, not tokens).
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120


def chunk_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    normalized = text.strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0
    length = len(normalized)
    while start < length:
        end = min(start + chunk_size, length)
        chunks.append(normalized[start:end])
        if end >= length:
            break
        start = max(end - overlap, start + 1)
    return chunks


def hash_content(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def title_from_markdown(path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()[:300]
    return path.stem.replace("-", " ").replace("_", " ").strip()[:300]

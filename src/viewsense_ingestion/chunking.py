from __future__ import annotations


def chunk_text(text: str, max_characters: int, overlap: int = 0) -> list[str]:
    """Deterministic paragraph-aware chunking with a hard size limit."""
    if max_characters < 100:
        raise ValueError("max_characters must be at least 100")
    if overlap < 0 or overlap >= max_characters:
        raise ValueError("overlap must be non-negative and smaller than max_characters")
    paragraphs = [part.strip() for part in text.replace("\r\n", "\n").split("\n\n") if part.strip()]
    def split_oversized(value: str) -> list[str]:
        parts: list[str] = []
        start = 0
        while start < len(value):
            end = min(start + max_characters, len(value))
            if end < len(value):
                boundary = value.rfind(" ", start + max_characters // 2, end + 1)
                if boundary > start:
                    end = boundary
            part = value[start:end].strip()
            if part:
                parts.append(part)
            if end >= len(value):
                break
            next_start = max(end - overlap, start + 1)
            while next_start < len(value) and value[next_start].isspace():
                next_start += 1
            start = next_start
        return parts

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(paragraph) > max_characters:
            if current:
                chunks.append(current)
                current = ""
            chunks.extend(split_oversized(paragraph))
        elif not current:
            current = paragraph
        elif len(current) + 2 + len(paragraph) <= max_characters:
            current += "\n\n" + paragraph
        else:
            chunks.append(current)
            prefix = current[-overlap:].strip() if overlap else ""
            candidate = f"{prefix}\n\n{paragraph}" if prefix else paragraph
            current = candidate if len(candidate) <= max_characters else paragraph
    if current:
        chunks.append(current)
    return chunks

"""
app/tools/rag_tool.py
RAG Tool — reusable retrieval tool for all LLM agents.
Phase 3: Extended with metadata (category, condition, type) and
         retrieve_with_metadata() for structured citation support.
ChromaDB is NOT replaced — this wraps it.
"""
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from app.rag.vector_store import query_similar_chunks

logger = logging.getLogger(__name__)

_MIN_SCORE: float = 0.0


# ── Data models ────────────────────────────────────────────────────────────────

class RetrievedChunk(BaseModel):
    id: str
    source: str
    text: str
    score: float = Field(ge=0.0, le=1.0)
    # Phase 3 additions — metadata from knowledge base
    category: str = Field(default="general", description="Medical category: cardiac, neurological, hepatic, etc.")
    condition: str = Field(default="", description="Specific condition name if available.")
    type: str = Field(default="medical_knowledge")


class KnowledgeSource(BaseModel):
    """Citation-ready source reference — used in API response knowledge_sources field."""
    source: str = Field(description="Source filename, e.g. diseases.md")
    topic: str = Field(description="Human-readable topic label.")
    category: str = Field(default="general")
    condition: str = Field(default="")


# ── Core retrieve ──────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: int = 3,
    min_score: float = _MIN_SCORE,
) -> List[RetrievedChunk]:
    """
    Query ChromaDB and return typed RetrievedChunk objects with full metadata.
    Returns empty list on any error — never raises.
    """
    if not query or not query.strip():
        logger.warning("RAG Tool: empty query received, skipping retrieval.")
        return []

    try:
        raw = query_similar_chunks(query.strip(), top_k=top_k)
    except Exception as exc:
        logger.error("RAG Tool: ChromaDB query failed. Error: %s", exc)
        return []

    chunks: List[RetrievedChunk] = []
    for item in raw:
        try:
            score = float(item.get("score", 0.0))
            if score < min_score:
                continue
            chunks.append(RetrievedChunk(
                id=str(item.get("id", "")),
                source=str(item.get("source", "unknown")),
                text=str(item.get("text", "")),
                score=round(score, 4),
                category=str(item.get("category", "general")),
                condition=str(item.get("condition", "")),
                type=str(item.get("type", "medical_knowledge")),
            ))
        except Exception as exc:
            logger.warning("RAG Tool: skipping malformed chunk. Error: %s", exc)
            continue

    return sorted(chunks, key=lambda c: c.score, reverse=True)


# ── Convenience wrappers ───────────────────────────────────────────────────────

def retrieve_as_context(
    query: str,
    top_k: int = 3,
    min_score: float = _MIN_SCORE,
) -> str:
    """
    Retrieve and format chunks as a single LLM-ready context string.
    Includes source, category, and relevance score in headers.
    """
    chunks = retrieve(query, top_k=top_k, min_score=min_score)
    if not chunks:
        return "No relevant medical context found in the knowledge base."

    parts = []
    for i, chunk in enumerate(chunks, 1):
        header = (
            f"[Medical Reference {i} | Source: {chunk.source} "
            f"| Category: {chunk.category} | Relevance: {chunk.score:.2f}]"
        )
        parts.append(header + "\n" + chunk.text)

    return "\n\n".join(parts)


def retrieve_as_dicts(
    query: str,
    top_k: int = 3,
    min_score: float = _MIN_SCORE,
) -> List[dict]:
    """Retrieve chunks as plain dicts for API serialization."""
    return [c.model_dump() for c in retrieve(query, top_k=top_k, min_score=min_score)]


def retrieve_with_metadata(
    symptoms: str,
    possible_conditions: List[str],
    top_k: int = 5,
) -> dict:
    """
    Part 3 improved retrieval — builds a richer combined query from symptoms
    and conditions, returns structured result with context, sources, confidence,
    and retrieved_topics.

    Returns:
        {
          "context":          str,
          "sources":          List[KnowledgeSource],
          "confidence":       str,   # "high" / "moderate" / "low" / "none"
          "retrieved_topics": List[str],
        }
    """
    conditions_text = ", ".join(possible_conditions) if possible_conditions else ""
    query = symptoms.strip()
    if conditions_text:
        query = query + ". Related conditions: " + conditions_text

    chunks = retrieve(query=query, top_k=top_k)

    if not chunks:
        return {
            "context": "No relevant medical knowledge could be retrieved at this time.",
            "sources": [],
            "confidence": "none",
            "retrieved_topics": [],
        }

    # Build context string
    parts = []
    seen_sources: dict = {}   # source filename → KnowledgeSource
    topics: List[str] = []

    for i, chunk in enumerate(chunks, 1):
        parts.append(
            f"[Medical Reference {i} | Source: {chunk.source} "
            f"| Category: {chunk.category} | Relevance: {chunk.score:.2f}]\n"
            f"{chunk.text}"
        )
        if chunk.source not in seen_sources:
            topic = _source_to_topic(chunk.source)
            seen_sources[chunk.source] = KnowledgeSource(
                source=chunk.source,
                topic=topic,
                category=chunk.category,
                condition=chunk.condition,
            )
            if topic not in topics:
                topics.append(topic)

    # Confidence based on top score
    top_score = chunks[0].score if chunks else 0.0
    if top_score >= 0.75:
        confidence = "high"
    elif top_score >= 0.45:
        confidence = "moderate"
    elif top_score > 0.0:
        confidence = "low"
    else:
        confidence = "none"

    return {
        "context":          "\n\n".join(parts),
        "sources":          list(seen_sources.values()),
        "confidence":       confidence,
        "retrieved_topics": topics,
    }


def _source_to_topic(filename: str) -> str:
    """Convert source filename to a readable topic: 'diseases.md' → 'Diseases'"""
    return (
        filename
        .replace(".md", "")
        .replace(".txt", "")
        .replace("_", " ")
        .replace("-", " ")
        .title()
    )

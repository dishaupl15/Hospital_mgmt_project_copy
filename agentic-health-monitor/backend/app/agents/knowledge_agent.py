"""
app/agents/knowledge_agent.py
MedicalKnowledgeAgent — structured retrieval layer over the upgraded RAG system.

Phase 3 upgrade:
- Uses retrieve_with_metadata() for richer combined query
- Returns sources as KnowledgeSource objects for citation support
- Exposes confidence and retrieved_topics
- Safe fallback on any failure, never raises
"""
import logging
from typing import List
from pydantic import BaseModel, Field
from app.tools.rag_tool import retrieve_with_metadata, KnowledgeSource

logger = logging.getLogger(__name__)


# ── Output model ───────────────────────────────────────────────────────────────

class KnowledgeResult(BaseModel):
    knowledge_context: str = Field(
        description="Formatted medical knowledge text ready to inject into LLM prompts."
    )
    sources: List[str] = Field(
        description="List of source document filenames.",
        default_factory=list,
    )
    knowledge_sources: List[KnowledgeSource] = Field(
        description="Structured citation-ready source objects with topic and category.",
        default_factory=list,
    )
    retrieved_topics: List[str] = Field(
        description="Human-readable topic labels from retrieved documents.",
        default_factory=list,
    )
    confidence: str = Field(
        default="none",
        description="Retrieval confidence: high / moderate / low / none.",
    )
    chunk_count: int = Field(
        description="Number of knowledge chunks retrieved.",
        default=0,
    )


# ── Agent function ─────────────────────────────────────────────────────────────

def retrieve_medical_knowledge(
    symptoms: str,
    possible_conditions: List[str],
    top_k: int = 5,
) -> KnowledgeResult:
    """
    MedicalKnowledgeAgent — queries the upgraded RAG system with a combined
    symptoms + conditions query and returns structured knowledge with citations.

    Returns KnowledgeResult on success, safe empty result on failure.
    Never raises.
    """
    conditions_text = ", ".join(possible_conditions) if possible_conditions else "none"
    print(
        "[KNOWLEDGE AGENT] Querying RAG | symptoms_len=" + str(len(symptoms)) +
        " | conditions=" + conditions_text + " | top_k=" + str(top_k)
    )

    try:
        result = retrieve_with_metadata(
            symptoms=symptoms,
            possible_conditions=possible_conditions,
            top_k=top_k,
        )
    except Exception as exc:
        logger.error("[KnowledgeAgent] retrieve_with_metadata failed: %s", exc)
        print("[KNOWLEDGE AGENT] FAILED: " + str(exc) + " — returning empty context")
        return _empty_result()

    sources_obj: List[KnowledgeSource] = result.get("sources", [])
    source_filenames = [s.source for s in sources_obj]
    topics = result.get("retrieved_topics", [])
    confidence = result.get("confidence", "none")
    context = result.get("context", "")

    if not context or confidence == "none":
        print("[KNOWLEDGE AGENT] No relevant chunks — returning empty context")
        return _empty_result()

    # Count chunks from the context (each starts with [Medical Reference N])
    chunk_count = context.count("[Medical Reference ")

    logger.info(
        "[KnowledgeAgent] chunks=%d | confidence=%s | sources=%s | topics=%s",
        chunk_count, confidence, source_filenames, topics,
    )
    print(
        "[KNOWLEDGE AGENT] OK — chunks=" + str(chunk_count) +
        " | confidence=" + confidence +
        " | sources=" + str(source_filenames)
    )

    return KnowledgeResult(
        knowledge_context=context,
        sources=source_filenames,
        knowledge_sources=sources_obj,
        retrieved_topics=topics,
        confidence=confidence,
        chunk_count=chunk_count,
    )


def _empty_result() -> KnowledgeResult:
    return KnowledgeResult(
        knowledge_context="No relevant medical knowledge could be retrieved at this time.",
        sources=[],
        knowledge_sources=[],
        retrieved_topics=[],
        confidence="none",
        chunk_count=0,
    )

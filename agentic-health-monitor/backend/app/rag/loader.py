"""
app/rag/loader.py
Document loader for the medical knowledge base.
Loads both legacy .txt files (medical_docs/) and structured .md files (knowledge_base/).
Each chunk carries structured metadata: category, condition, source, type.
"""
import re
from pathlib import Path
from typing import Dict, List, Optional

# Legacy txt docs path (kept for backward compatibility)
MEDICAL_DOCS_PATH = Path(__file__).resolve().parents[3] / "medical_docs"

# New structured knowledge base path
KNOWLEDGE_BASE_PATH = Path(__file__).resolve().parent / "knowledge_base"

# Category keywords extracted from filenames and content headers
_CATEGORY_MAP = {
    "cardiac":          ["cardiac", "heart", "chest_pain", "angina", "arrhythmia"],
    "neurological":     ["neurological", "neuro", "stroke", "migraine", "meningitis", "tia", "seizure"],
    "hepatic":          ["hepatic", "liver", "jaundice", "hepatitis", "cirrhosis"],
    "respiratory":      ["respiratory", "respiratory", "pneumonia", "asthma", "pulmonary", "copd"],
    "gastrointestinal": ["gastrointestinal", "gastro", "appendicitis", "ulcer", "peptic", "abdominal"],
    "endocrine":        ["endocrine", "diabetes", "dka", "hypoglycemia", "thyroid"],
    "musculoskeletal":  ["musculoskeletal", "fracture", "dvt", "joint", "arthritis"],
    "systemic":         ["systemic", "sepsis", "dengue", "infection", "fever"],
    "emergency":        ["emergency", "urgent", "immediate"],
    "prevention":       ["prevention", "wellness", "screening"],
}


def _infer_category(text: str, filename: str) -> str:
    """Infer the medical category from content and filename."""
    combined = (filename + " " + text[:200]).lower()
    for category, keywords in _CATEGORY_MAP.items():
        if any(kw in combined for kw in keywords):
            return category
    return "general"


def _infer_condition(text: str) -> str:
    """Extract condition name from structured md content (e.g. '- condition: stroke')."""
    match = re.search(r"-\s*condition:\s*([a-z_]+)", text.lower())
    return match.group(1) if match else ""


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
    """Split text into overlapping chunks by word count."""
    text = re.sub(r"\s+", " ", text.strip())
    if not text:
        return []
    words = text.split(" ")
    chunks: List[str] = []
    current: List[str] = []
    for word in words:
        current.append(word)
        if len(" ".join(current)) >= chunk_size:
            chunks.append(" ".join(current).strip())
            overlap_words = current[-overlap:] if overlap < len(current) else current
            current = overlap_words.copy()
    if current:
        chunks.append(" ".join(current).strip())
    return chunks


def _load_txt_files() -> List[Dict[str, str]]:
    """Load legacy .txt files from medical_docs/ with inferred metadata."""
    documents: List[Dict[str, str]] = []
    if not MEDICAL_DOCS_PATH.exists():
        return documents
    for path in sorted(MEDICAL_DOCS_PATH.glob("*.txt")):
        if not path.is_file():
            continue
        raw_text = path.read_text(encoding="utf-8").strip()
        for idx, chunk in enumerate(chunk_text(raw_text)):
            category = _infer_category(chunk, path.stem)
            documents.append({
                "id":        f"{path.stem}_{idx}",
                "source":    path.name,
                "text":      chunk,
                "category":  category,
                "condition": _infer_condition(chunk),
                "type":      "medical_knowledge",
            })
    return documents


def _load_md_files() -> List[Dict[str, str]]:
    """Load structured .md files from knowledge_base/ with full metadata."""
    documents: List[Dict[str, str]] = []
    if not KNOWLEDGE_BASE_PATH.exists():
        return documents
    for path in sorted(KNOWLEDGE_BASE_PATH.glob("*.md")):
        if not path.is_file():
            continue
        raw_text = path.read_text(encoding="utf-8").strip()
        # Split on markdown section headers (## or ###) to create natural chunks
        sections = re.split(r"\n(?=#{2,3}\s)", raw_text)
        for idx, section in enumerate(sections):
            section = section.strip()
            if not section or len(section) < 50:
                continue
            # For long sections, further chunk them
            sub_chunks = chunk_text(section, chunk_size=500, overlap=60)
            for sub_idx, chunk in enumerate(sub_chunks):
                chunk_id = f"{path.stem}_{idx}_{sub_idx}"
                category = _infer_category(chunk, path.stem)
                documents.append({
                    "id":        chunk_id,
                    "source":    path.name,
                    "text":      chunk,
                    "category":  category,
                    "condition": _infer_condition(chunk),
                    "type":      "medical_knowledge",
                })
    return documents


def load_documents() -> List[Dict[str, str]]:
    """
    Load all medical knowledge documents.
    Returns combined list from legacy .txt files and new .md knowledge base.
    Each item has: id, source, text, category, condition, type.
    """
    txt_docs = _load_txt_files()
    md_docs = _load_md_files()
    all_docs = txt_docs + md_docs
    print(
        f"[LOADER] Loaded {len(txt_docs)} chunks from .txt files + "
        f"{len(md_docs)} chunks from .md knowledge base = {len(all_docs)} total"
    )
    return all_docs

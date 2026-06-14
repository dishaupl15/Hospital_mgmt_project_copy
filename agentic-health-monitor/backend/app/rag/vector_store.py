from pathlib import Path
from typing import Dict, List

import chromadb

from app.rag.embedder import create_embeddings
from app.rag.loader import load_documents
from app.core.config import get_settings

CHROMA_PERSIST_PATH = Path(__file__).resolve().parents[2] / ".chromadb"

# New Chroma client
client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_PATH))


def get_collection():
    return client.get_or_create_collection(name=get_settings().chroma_collection_name)


def build_collection(force_reindex: bool = False):
    collection_name = get_settings().chroma_collection_name
    if force_reindex:
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass

    collection = get_collection()

    try:
        count = collection.count()
    except Exception:
        count = 0

    if force_reindex or count == 0:
        chunks = load_documents()

        if chunks:
            ids = [chunk["id"] for chunk in chunks]
            metadatas = [
                {
                    "source":    chunk.get("source", ""),
                    "category":  chunk.get("category", "general"),
                    "condition": chunk.get("condition", ""),
                    "type":      chunk.get("type", "medical_knowledge"),
                }
                for chunk in chunks
            ]
            documents = [chunk["text"] for chunk in chunks]
            embeddings = create_embeddings(documents)

            collection.add(
                ids=ids,
                metadatas=metadatas,
                documents=documents,
                embeddings=embeddings,
            )

    return collection


def query_similar_chunks(query: str, top_k: int = 3) -> List[Dict[str, object]]:
    collection = build_collection()

    query_embedding = create_embeddings([query])[0]

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    output = []
    for idx, (id_value, doc, metadata, distance) in enumerate(
        zip(ids, documents, metadatas, distances)
    ):
        meta = metadata if isinstance(metadata, dict) else {}
        output.append(
            {
                "id":        id_value if id_value is not None else f"result_{idx}",
                "source":    meta.get("source", ""),
                "category":  meta.get("category", "general"),
                "condition": meta.get("condition", ""),
                "type":      meta.get("type", "medical_knowledge"),
                "text":      doc,
                "score":     1.0 - distance if distance is not None else 0.0,
            }
        )

    return output

#python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
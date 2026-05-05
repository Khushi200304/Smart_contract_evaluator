import os
import re
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.config import settings
from app.models import ContractChunk

if TYPE_CHECKING:
    pass


def _split_chunks(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    if not text.strip():
        return []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append(chunk.strip())
        i += chunk_size - overlap
    return chunks


def _chroma_ok() -> bool:
    try:
        import chromadb  # noqa: F401

        return True
    except ImportError:
        return False


def _collection_name(contract_id: int) -> str:
    return f"contract_{contract_id}"


def _index_chroma(contract_id: int, chunks: list[str]) -> None:
    import chromadb
    from chromadb.utils import embedding_functions

    os.makedirs(settings.chroma_path, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_path)
    name = _collection_name(contract_id)
    try:
        client.delete_collection(name)
    except Exception:
        pass
    col = client.get_or_create_collection(
        name=name,
        embedding_function=embedding_functions.DefaultEmbeddingFunction(),
    )
    ids = [f"{contract_id}_{j}" for j in range(len(chunks))]
    col.add(ids=ids, documents=chunks, metadatas=[{"contract_id": contract_id}] * len(chunks))


def _query_chroma(contract_id: int, question: str, n_results: int) -> tuple[str, list[str]]:
    import chromadb
    from chromadb.utils import embedding_functions

    client = chromadb.PersistentClient(path=settings.chroma_path)
    name = _collection_name(contract_id)
    try:
        col = client.get_collection(
            name=name,
            embedding_function=embedding_functions.DefaultEmbeddingFunction(),
        )
    except Exception:
        return "", []
    res = col.query(query_texts=[question], n_results=n_results)
    docs = (res.get("documents") or [[]])[0]
    if not docs:
        return "", []
    return "\n\n---\n\n".join(docs), docs


def index_contract_text(db: Session, contract_id: int, text: str) -> None:
    chunks = _split_chunks(text)
    db.query(ContractChunk).filter(ContractChunk.contract_id == contract_id).delete()
    for idx, c in enumerate(chunks):
        db.add(ContractChunk(contract_id=contract_id, chunk_index=idx, text=c))
    db.commit()
    if _chroma_ok() and chunks:
        try:
            _index_chroma(contract_id, chunks)
        except Exception:
            pass


def _keyword_query(db: Session, contract_id: int, question: str, n_results: int) -> tuple[str, list[str]]:
    rows = (
        db.query(ContractChunk)
        .filter(ContractChunk.contract_id == contract_id)
        .order_by(ContractChunk.chunk_index)
        .all()
    )
    if not rows:
        return "", []
    qwords = set(re.findall(r"\w+", question.lower()))
    if not qwords:
        top = [r.text for r in rows[:n_results]]
        return "\n\n---\n\n".join(top), top
    scored: list[tuple[int, str]] = []
    for r in rows:
        words = set(re.findall(r"\w+", r.text.lower()))
        scored.append((len(qwords & words), r.text))
    scored.sort(key=lambda x: -x[0])
    best_score = scored[0][0] if scored else 0
    if best_score == 0:
        top = [t for _, t in scored[:n_results]]
    else:
        top = [t for s, t in scored[:n_results] if s > 0]
        if not top:
            top = [t for _, t in scored[:n_results]]
    return "\n\n---\n\n".join(top), top


def query_contract(db: Session, contract_id: int, question: str, n_results: int = 5) -> tuple[str, list[str]]:
    if _chroma_ok():
        try:
            ctx, docs = _query_chroma(contract_id, question, n_results)
            if ctx:
                return ctx, docs
        except Exception:
            pass
    return _keyword_query(db, contract_id, question, n_results)

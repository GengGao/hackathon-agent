import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Iterable
import threading
import hashlib
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from models.db import list_active_rules, list_active_rule_rows
import sqlite3

# Choose a small embedding model that runs locally (e.g., all-MiniLM-L6-v2)
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")  # global singleton model
DIM = EMBED_MODEL.get_sentence_embedding_dimension()

# Default similarity cutoff (cosine). Results below are filtered out.
DEFAULT_SIMILARITY_CUTOFF = 0.0  # Backward compatible (no filtering by default)

_GLOBAL_RAG_INSTANCE: Optional["RuleRAG"] = None

def get_rag() -> "RuleRAG":
    """Return process-wide singleton RuleRAG instance (lazy)."""
    global _GLOBAL_RAG_INSTANCE
    if _GLOBAL_RAG_INSTANCE is None:
        _GLOBAL_RAG_INSTANCE = RuleRAG()
    return _GLOBAL_RAG_INSTANCE

class RuleRAG:
    """RAG over hackathon rules & user-provided context stored in DB.

    Uses cosine similarity (normalized vectors + IndexFlatIP). Higher score better.
    """

    def __init__(
        self,
        rules_path: Optional[Path] = None,
        *,
        prebuilt_index: Optional[faiss.Index] = None,
        prebuilt_chunks: Optional[List[str]] = None,
        prebuilt_embeddings: Optional[np.ndarray] = None,
        similarity_cutoff: float = DEFAULT_SIMILARITY_CUTOFF,
        lazy: bool = True,
    ):
        self.rules_path = rules_path
        self.index: Optional[faiss.Index] = prebuilt_index
        self.chunks: List[str] = prebuilt_chunks or []
        self.embeddings: Optional[np.ndarray] = prebuilt_embeddings
        self.metadata: List[Dict[str, Any]] = []  # parallel to chunks (chunk-level metadata)
        self.similarity_cutoff = similarity_cutoff
        self._last_rules_hash: Optional[str] = None
        self._lock = threading.RLock()
        if not lazy and self.index is None:
            self.rebuild(force=True)

    def _gather_corpus(self) -> List[Dict[str, Any]]:
        """Return list of rule documents with metadata keys: id, source, filename, content.

        Falls back to file if DB yields nothing.
        """
        rows: List[Dict[str, Any]] = []
        try:
            rows = list_active_rule_rows()
        except (sqlite3.OperationalError, Exception):
            rows = []
        if rows:
            return rows
        if self.rules_path and self.rules_path.exists():
            return [{
                "id": None,
                "source": "file",
                "filename": self.rules_path.name,
                "content": self.rules_path.read_text(encoding='utf-8')
            }]
        return []

    def _compute_rules_hash(self, docs: Iterable[Dict[str, Any]]) -> str:
        h = hashlib.sha256()
        for d in docs:
            # Include id + source + filename + content for change detection
            key = f"{d.get('id')}|{d.get('source')}|{d.get('filename')}|{d.get('content')}\n"
            h.update(key.encode('utf-8'))
        return h.hexdigest()

    def rebuild(self, force: bool = False) -> bool:
        """Rebuild the FAISS index if rules changed or force requested.

        Returns True if a rebuild occurred, False otherwise.
        """
        with self._lock:
            docs = self._gather_corpus() or []
            rules_hash = self._compute_rules_hash(docs)
            if not force and self._last_rules_hash == rules_hash and self.index is not None:
                return False  # No change

            # Chunking: split each doc's content by blank lines (keep metadata per chunk)
            new_chunks: List[str] = []
            new_metadata: List[Dict[str, Any]] = []
            for d in docs:
                raw = d.get("content", "")
                parts = [c.strip() for c in raw.split('\n\n') if c.strip()]
                if not parts:
                    parts = [raw.strip()] if raw.strip() else []
                for p in parts:
                    new_chunks.append(p)
                    new_metadata.append({
                        "rule_id": d.get("id"),
                        "source": d.get("source"),
                        "filename": d.get("filename"),
                        "length": len(p),
                    })
            if not new_chunks:
                new_chunks = ["No rules/context available."]
                new_metadata = [{"rule_id": None, "source": "none", "filename": None, "length": 0}]

            embs = EMBED_MODEL.encode(new_chunks, batch_size=32, show_progress_bar=False)
            embs = np.array(embs).astype('float32')
            faiss.normalize_L2(embs)

            self.chunks = new_chunks
            self.metadata = new_metadata
            self.embeddings = embs
            self.index = faiss.IndexFlatIP(DIM)
            self.index.add(self.embeddings)
            self._last_rules_hash = rules_hash
            return True

    def ensure_index(self):
        """Ensure index exists (lazy build)."""
        if self.index is None:
            self.rebuild(force=True)

    def retrieve(self, query: str, k: int = 5, include_metadata: bool = False) -> List[Any]:
        """Retrieve top-k relevant chunks with metadata.

        Returns list of tuples: (text, score, metadata)
        Filters out results below similarity_cutoff.
        """
        self.ensure_index()
        assert self.index is not None
        q_vec = EMBED_MODEL.encode([query])[0].astype('float32')
        q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-12)  # normalize for cosine
        D, I = self.index.search(np.array([q_vec]).astype('float32'), k)
        results_full: List[Tuple[str, float, Dict[str, Any]]] = []
        for rank_idx, chunk_idx in enumerate(I[0]):
            if chunk_idx == -1:
                continue
            score = float(D[0][rank_idx])
            if score < self.similarity_cutoff:
                continue
            meta = self.metadata[chunk_idx] if chunk_idx < len(self.metadata) else {}
            results_full.append((self.chunks[chunk_idx], score, meta))
        # Fallback: if no results pass cutoff but there are chunks, return best raw top-1
        if not results_full and len(self.chunks) > 0:
            # Use original ranking irrespective of cutoff
            for rank_idx, chunk_idx in enumerate(I[0]):
                if chunk_idx == -1:
                    continue
                score = float(D[0][rank_idx])
                meta = self.metadata[chunk_idx] if chunk_idx < len(self.metadata) else {}
                results_full.append((self.chunks[chunk_idx], score, meta))
                break
        if include_metadata:
            return results_full
        # Backward compatible: strip metadata
        return [(c, s) for (c, s, _m) in results_full]
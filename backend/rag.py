import os
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Iterable
import threading
import hashlib
import time
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from models.db import list_active_rules, list_active_rule_rows
import sqlite3
import json

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
        self._is_rebuilding: bool = False
        self._last_built_at: Optional[float] = None
        self._session_id: Optional[str] = None

        # Cache location (under backend/data/rag_cache)
        try:
            from models.db import DATA_DIR  # lazy import to avoid circular at module import time
            self._cache_root: Path = Path(DATA_DIR) / "rag_cache"
        except Exception:
            self._cache_root = Path(__file__).resolve().parents[1] / "data" / "rag_cache"
        self._cache_root.mkdir(parents=True, exist_ok=True)
        if not lazy and self.index is None:
            # Attempt to load from cache on startup for fast warm start
            self.rebuild(force=False)

    def set_session(self, session_id: Optional[str]) -> None:
        """Scope this RAG instance to a specific chat session.

        Passing None resets to global context only.
        """
        with self._lock:
            if self._session_id == session_id:
                return
            self._session_id = session_id
            # Force rebuild on next ensure/retrieval by clearing hash
            self._last_rules_hash = None

    def _gather_corpus(self) -> List[Dict[str, Any]]:
        """Return list of rule documents with metadata keys: id, source, filename, content.

        Falls back to file if DB yields nothing.
        """
        rows: List[Dict[str, Any]] = []
        try:
            rows = list_active_rule_rows(self._session_id)
        except (sqlite3.OperationalError, Exception):
            rows = []
        if rows:
            # If any user-provided context exists in the current scope, exclude seeded initial rules.
            try:
                has_any_non_initial = any(r.get("source") != "initial" for r in rows)
                if has_any_non_initial:
                    rows = [r for r in rows if r.get("source") != "initial"]
            except Exception:
                # Be permissive: if anything goes wrong, return as-is
                pass
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

    def _cache_dir_for_hash(self, rules_hash: str) -> Path:
        return self._cache_root / rules_hash

    def _try_load_cache(self, rules_hash: str) -> bool:
        """Load chunks, metadata, embeddings, and FAISS index from cache if available."""
        try:
            cdir = self._cache_dir_for_hash(rules_hash)
            chunks_path = cdir / "chunks.json"
            meta_path = cdir / "meta.json"
            embs_path = cdir / "embeddings.npy"
            if not (chunks_path.exists() and meta_path.exists() and embs_path.exists()):
                return False
            with chunks_path.open("r", encoding="utf-8") as f:
                cached_chunks = json.load(f)
            with meta_path.open("r", encoding="utf-8") as f:
                cached_meta = json.load(f)
            cached_embs = np.load(embs_path)

            if not isinstance(cached_chunks, list) or not isinstance(cached_meta, list):
                return False
            if cached_embs is None or len(cached_chunks) == 0:
                return False

            # Rebuild FAISS index from embeddings
            faiss.normalize_L2(cached_embs)
            index = faiss.IndexFlatIP(DIM)
            index.add(cached_embs.astype("float32"))

            self.chunks = cached_chunks
            self.metadata = cached_meta
            self.embeddings = cached_embs.astype("float32")
            self.index = index
            self._last_rules_hash = rules_hash
            self._last_built_at = time.time()
            return True
        except Exception:
            return False

    def _save_cache(self, rules_hash: str, chunks: List[str], metadata: List[Dict[str, Any]], embeddings: np.ndarray) -> None:
        try:
            cdir = self._cache_dir_for_hash(rules_hash)
            cdir.mkdir(parents=True, exist_ok=True)
            (cdir / "chunks.json").write_text(json.dumps(chunks, ensure_ascii=False), encoding="utf-8")
            (cdir / "meta.json").write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
            np.save(cdir / "embeddings.npy", embeddings.astype("float32"))
        except Exception:
            # Best-effort cache; ignore failures
            pass

    def rebuild(self, force: bool = False) -> bool:
        """Rebuild the FAISS index if rules changed or force requested.

        Returns True if a rebuild occurred, False otherwise.
        """
        with self._lock:
            if self._is_rebuilding:
                # Another rebuild is already in progress
                return False
            self._is_rebuilding = True
            docs = self._gather_corpus() or []
            rules_hash = self._compute_rules_hash(docs)
            if not force and self._last_rules_hash == rules_hash and self.index is not None:
                self._is_rebuilding = False
                return False  # No change

            try:
                # If not forcing a rebuild, try loading from cache first
                if not force and self._try_load_cache(rules_hash):
                    return True
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
                self._last_built_at = time.time()
                # Persist cache for warm starts
                self._save_cache(rules_hash, self.chunks, self.metadata, self.embeddings)
                return True
            finally:
                self._is_rebuilding = False

    def ensure_index(self):
        """Ensure index exists (lazy build with cache)."""
        if self.index is None or self._last_rules_hash is None:
            self.rebuild(force=False)

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

    def status(self) -> Dict[str, Any]:
        """Return current indexing status and metadata."""
        with self._lock:
            ready = (
                self.index is not None
                and self.embeddings is not None
                and len(self.chunks) > 0
                and self._last_rules_hash is not None
            )
            return {
                "ready": ready,
                "building": self._is_rebuilding,
                "chunks": len(self.chunks),
                "last_built_at": self._last_built_at,
                "rules_hash": self._last_rules_hash,
                "session_id": self._session_id,
            }

    def status_scoped(self, session_id: Optional[str]) -> Dict[str, Any]:
        """Atomically set session and return status to avoid cross-request races."""
        # RLock allows re-entrant acquisition within set_session and status
        with self._lock:
            self.set_session(session_id)
            return self.status()
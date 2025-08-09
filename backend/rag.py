import os
from pathlib import Path
from typing import List, Tuple
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Choose a small embedding model that runs locally (e.g., all-MiniLM-L6-v2)
EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
DIM = EMBED_MODEL.get_sentence_embedding_dimension()

class RuleRAG:
    """Simple rules Retrieval-Augmented component.

    Switched from L2 distance (IndexFlatL2) to cosine similarity via
    normalized vectors + IndexFlatIP. Returned scores are cosine similarity
    (higher is better, range roughly [-1,1]).
    """

    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.index = None         # FAISS index (IndexFlatIP over normalized vecs)
        self.chunks: List[str] = []
        self.embeddings = None    # np.ndarray (normalized float32)
        self._load_rules()

    def _load_rules(self):
        raw = self.rules_path.read_text(encoding="utf-8")
        # Simple chunker: split by double newlines
        raw_chunks = [c.strip() for c in raw.split("\n\n") if c.strip()]
        self.chunks = raw_chunks
        # Compute embeddings -> normalize for cosine similarity
        embs = EMBED_MODEL.encode(self.chunks, batch_size=32, show_progress_bar=False)
        embs = np.array(embs).astype('float32')
        faiss.normalize_L2(embs)
        self.embeddings = embs
        self.index = faiss.IndexFlatIP(DIM)
        self.index.add(self.embeddings)

    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        q_vec = EMBED_MODEL.encode([query])[0].astype('float32')
        # Normalize query for cosine
        q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-12)
        D, I = self.index.search(np.array([q_vec]).astype('float32'), k)
        # D are cosine similarities (dot products of normalized vectors)
        results = []
        for rank_idx, chunk_idx in enumerate(I[0]):
            if chunk_idx == -1:
                continue
            results.append((self.chunks[chunk_idx], float(D[0][rank_idx])))
        return results
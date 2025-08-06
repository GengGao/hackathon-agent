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
    def __init__(self, rules_path: Path):
        self.rules_path = rules_path
        self.index = None         # FAISS index
        self.chunks = []          # List[str]
        self.embeddings = None    # np.ndarray
        self._load_rules()

    def _load_rules(self):
        raw = self.rules_path.read_text(encoding="utf-8")
        # Simple chunker: split by double newlines, keep <= 200 words
        raw_chunks = [c.strip() for c in raw.split("\n\n") if c.strip()]
        self.chunks = raw_chunks
        # Compute embeddings
        self.embeddings = EMBED_MODEL.encode(self.chunks, batch_size=32, show_progress_bar=False)
        self.index = faiss.IndexFlatL2(DIM)
        self.index.add(np.array(self.embeddings).astype('float32'))

    def retrieve(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        q_vec = EMBED_MODEL.encode([query])[0]
        D, I = self.index.search(np.array([q_vec]).astype('float32'), k)
        results = [(self.chunks[i], float(D[0][idx])) for idx, i in enumerate(I[0])]
        return results
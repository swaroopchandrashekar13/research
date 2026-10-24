"""Dense retrieval for Study 1b: BAAI/bge-m3 dense embeddings, cosine similarity (preregistration_study1b §3.2)."""
from __future__ import annotations

import numpy as np

MODEL = "BAAI/bge-m3"
REVISION = "5617a9f61b028005a4858fdac845db406aefb181"  # pinned Hugging Face commit
MAX_SEQ_LENGTH = 8192  # no chunk (<= 512 words) is truncated


class Encoder:
    """Thin wrapper so tests can substitute a fake encoder with the same `encode(texts) -> [n, dim]` interface."""

    def __init__(self, device: str | None = None, batch_size: int = 32, cache_dir: str | None = None):
        import torch
        from sentence_transformers import SentenceTransformer

        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.model = SentenceTransformer(MODEL, revision=REVISION, device=self.device, cache_folder=cache_dir)
        self.model.max_seq_length = MAX_SEQ_LENGTH
        if self.device == "cuda":
            self.model.half()
        self.batch_size = batch_size
        self.name = f"{MODEL}@{REVISION[:12]}|{self.device}|{'fp16' if self.device == 'cuda' else 'fp32'}"

    def encode(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, 1024), dtype=np.float32)
        emb = self.model.encode(texts, batch_size=self.batch_size, normalize_embeddings=True,
                                convert_to_numpy=True, show_progress_bar=False)
        return np.asarray(emb, dtype=np.float32)


def dense_rank(chunk_emb: np.ndarray, query_emb: np.ndarray, depth: int, block: int = 256) -> np.ndarray:
    """[n_queries, depth] chunk indices by descending cosine similarity; ties keep the lower chunk index."""
    depth = min(depth, len(chunk_emb))
    out = np.empty((len(query_emb), depth), dtype=np.int64)
    for i in range(0, len(query_emb), block):
        sims = query_emb[i: i + block] @ chunk_emb.T
        out[i: i + block] = np.argsort(-sims, axis=1, kind="stable")[:, :depth]
    return out

"""Dense retrieval for Study 1b: BAAI/bge-m3 dense embeddings, cosine similarity (Study 1b analysis plan §3.2)."""
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

    def identity(self) -> dict:
        """Everything that can change an embedding: the cache key is a fingerprint of this (ragmv.run1b)."""
        from importlib import metadata

        import torch

        def ver(pkg):
            try:
                return metadata.version(pkg)
            except metadata.PackageNotFoundError:
                return None

        tok = getattr(self.model, "tokenizer", None)
        return {"model": MODEL, "revision": REVISION, "tokenizer_revision": REVISION,
                "tokenizer_class": type(tok).__name__ if tok is not None else None,
                "max_seq_length": int(self.model.max_seq_length), "normalize_embeddings": True,
                "compute_dtype": "float16" if self.device == "cuda" else "float32",
                "device_type": self.device, "device_name": torch.cuda.get_device_name(0) if self.device == "cuda" else "cpu",
                "batch_size": self.batch_size,
                "versions": {p: ver(p) for p in ("torch", "transformers", "sentence-transformers", "numpy")}}

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


def _block_sims(chunk_emb: np.ndarray, query_emb: np.ndarray, i: int, block: int) -> np.ndarray:
    """Similarities of query i, computed in the same block product as `dense_rank` (bit-identical values)."""
    start = (i // block) * block
    return (query_emb[start: start + block] @ chunk_emb.T)[i - start]


def dense_rank_filled(chunk_emb: np.ndarray, query_emb: np.ndarray, depth: int, chunk_words, budget: int,
                      block: int = 256):
    """`dense_rank` extended per query until `budget` words are ranked or the corpus is exhausted
    (`ragmv.budgetfill`). Only underfilled queries are re-ranked, one query at a time."""
    from .budgetfill import fill_to_budget

    ids = dense_rank(chunk_emb, query_emb, depth, block)
    scores = np.empty(ids.shape, dtype=np.float64)
    for i in range(len(query_emb)):
        scores[i] = _block_sims(chunk_emb, query_emb, i, block)[ids[i]]

    def retrieve_one(i: int, d: int):
        sims = _block_sims(chunk_emb, query_emb, i, block)
        order = np.argsort(-sims, kind="stable")[:d]
        return order.astype(np.int64), sims[order].astype(np.float64)

    return fill_to_budget(ids, scores, chunk_words, budget, len(chunk_emb), retrieve_one)

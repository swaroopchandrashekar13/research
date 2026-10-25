"""Embedding caches are bound to their full identity and validated on every read."""
import json

import numpy as np
import pytest

from ragmv import run1b


class CountingEncoder:
    """Deterministic fake encoder with an explicit identity."""

    def __init__(self, max_len=8192, dtype="float16"):
        self.calls, self.max_len, self.dtype = 0, max_len, dtype
        self.name = "counting"

    def identity(self):
        return {"model": "fake", "revision": "r1", "max_seq_length": self.max_len, "compute_dtype": self.dtype,
                "normalize_embeddings": True, "device_type": "cpu"}

    def encode(self, texts):
        self.calls += 1
        out = np.array([[len(t), t.count("a"), 1.0] for t in texts], dtype=np.float32)
        return out / np.linalg.norm(out, axis=1, keepdims=True)


TEXTS = ["alpha beta", "gamma", "a a a"]


def test_valid_hit_does_not_recompute_and_is_deterministic(tmp_path):
    enc = CountingEncoder()
    a = run1b.cached_embeddings(tmp_path, "chunks", TEXTS, enc, {"chunking": "x"})
    b = run1b.cached_embeddings(tmp_path, "chunks", TEXTS, enc, {"chunking": "x"})
    assert enc.calls == 1 and np.array_equal(a, b) and a.dtype == np.float16
    other = tmp_path / "other"
    c = run1b.cached_embeddings(other, "chunks", TEXTS, CountingEncoder(), {"chunking": "x"})
    assert np.array_equal(a, c)
    files = sorted(p.name for p in tmp_path.iterdir() if p.is_file())
    assert [f.split(".")[-1] for f in files] == ["json", "npz"]


@pytest.mark.parametrize("change", [
    lambda: (CountingEncoder(max_len=512), TEXTS, {"chunking": "x"}),       # different maximum length
    lambda: (CountingEncoder(dtype="float32"), TEXTS, {"chunking": "x"}),   # different numerical mode
    lambda: (CountingEncoder(), list(reversed(TEXTS)), {"chunking": "x"}),  # same texts, different order
    lambda: (CountingEncoder(), TEXTS, {"chunking": "y"}),                  # different preprocessing
])
def test_incompatible_settings_never_reuse_an_entry(tmp_path, change):
    run1b.cached_embeddings(tmp_path, "chunks", TEXTS, CountingEncoder(), {"chunking": "x"})
    enc, texts, prep = change()
    run1b.cached_embeddings(tmp_path, "chunks", texts, enc, prep)
    assert enc.calls == 1  # a miss: computed, not read from the first entry
    assert len(list(tmp_path.glob("emb-*.npz"))) == 2


def test_corrupt_entry_is_an_error_and_left_in_place(tmp_path):
    enc = CountingEncoder()
    run1b.cached_embeddings(tmp_path, "chunks", TEXTS, enc, {})
    npz = next(tmp_path.glob("emb-*.npz"))
    data = bytearray(npz.read_bytes())
    data[-10] ^= 0xFF
    npz.write_bytes(bytes(data))
    with pytest.raises(run1b.CacheError, match="corrupt"):
        run1b.cached_embeddings(tmp_path, "chunks", TEXTS, enc, {})
    assert npz.exists() and enc.calls == 1


def test_tampered_sidecar_identity_is_an_error(tmp_path):
    run1b.cached_embeddings(tmp_path, "chunks", TEXTS, CountingEncoder(), {})
    meta = next(tmp_path.glob("emb-*.json"))
    m = json.loads(meta.read_text())
    m["identity"]["encoder"]["revision"] = "r2"
    meta.write_text(json.dumps(m))
    with pytest.raises(run1b.CacheError, match="identity"):
        run1b.cached_embeddings(tmp_path, "chunks", TEXTS, CountingEncoder(), {})


def test_incomplete_entry_is_an_error(tmp_path):
    run1b.cached_embeddings(tmp_path, "chunks", TEXTS, CountingEncoder(), {})
    next(tmp_path.glob("emb-*.json")).unlink()
    with pytest.raises(run1b.CacheError, match="incomplete"):
        run1b.cached_embeddings(tmp_path, "chunks", TEXTS, CountingEncoder(), {})


def test_non_finite_embeddings_are_refused(tmp_path):
    class Bad(CountingEncoder):
        def encode(self, texts):
            return np.full((len(texts), 3), np.nan)
    with pytest.raises(run1b.CacheError, match="non-finite"):
        run1b.cached_embeddings(tmp_path, "chunks", TEXTS, Bad(), {})
    assert not list(tmp_path.glob("emb-*"))


def test_legacy_cache_files_are_ignored_not_trusted_not_deleted(tmp_path, capsys):
    legacy = tmp_path / "sentences_0123456789ab.npz"
    np.savez_compressed(legacy, a=np.zeros((3, 3), dtype=np.float16))
    assert run1b.warn_legacy_caches(tmp_path) == [legacy.name]
    assert "ignored" in capsys.readouterr().err
    enc = CountingEncoder()
    run1b.cached_embeddings(tmp_path, "sentences", TEXTS, enc, {})
    assert enc.calls == 1 and legacy.exists()


def test_encoder_without_identity_is_marked_untrusted():
    class Plain:
        name = "plain"

        def encode(self, texts):
            return np.ones((len(texts), 2))
    assert "untrusted_encoder" in run1b.encoder_identity(Plain())

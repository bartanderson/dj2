# world/embedding_model.py
#
# Lightweight embedding wrapper using all-MiniLM-L6-v2 (384-dim, ~22MB).
# Lazy-loads on first use -- no startup cost unless embeddings are needed.
# Normalized embeddings means cosine similarity = dot product.

import numpy as np

_model = None


def get_model():
    global _model
    if _model is None:
        import logging
        logging.getLogger("torch.distributed.elastic").setLevel(logging.ERROR)
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def embed_text(text: str) -> np.ndarray:
    """Embed a string. Returns a normalized 384-dim vector."""
    return get_model().encode(text, normalize_embeddings=True)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity of two normalized vectors = dot product."""
    return float(np.dot(a, b))

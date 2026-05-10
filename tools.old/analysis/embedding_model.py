# embedding_model.py
import numpy as np
from sentence_transformers import SentenceTransformer

_model = None

def get_model():
    global _model
    if _model is None:
        # Using a small, fast model (384-dim)
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model

def embed_text(text: str) -> np.ndarray:
    model = get_model()
    return model.encode(text, normalize_embeddings=True)  # normalized for cosine similarity

def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return np.dot(a, b)  # because both are normalized
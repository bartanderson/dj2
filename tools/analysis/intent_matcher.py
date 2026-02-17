"""Intent matching using embeddings."""
import sqlite3
import json
import numpy as np
from pathlib import Path
from typing import List, Tuple, Dict, Optional
from tools.analysis.embedding_model import embed_text, cosine_similarity

def _get_top_files_for_intent(intent: str, db_path: Path, categories_path: Optional[str] = None,
                              max_files: int = 5, verbose: bool = False) -> List[Tuple[str, float, Dict]]:
    """
    Find files matching the intent using embedding similarity.
    Returns list of (file_path, similarity_score, file_data).
    """
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Check if embeddings table exists and has data
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='file_embeddings'")
    if cur.fetchone():
        intent_emb = embed_text(intent)
        rows = cur.execute("SELECT file_path, embedding FROM file_embeddings").fetchall()
        scores = []
        for file_path, emb_bytes in rows:
            emb = np.frombuffer(emb_bytes, dtype=np.float32)
            sim = cosine_similarity(intent_emb, emb)
            scores.append((file_path, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        top_paths = [file_path for file_path, _ in scores[:max_files]]
        result = []
        for file_path in top_paths:
            row = cur.execute("SELECT data FROM files WHERE path = ?", (file_path,)).fetchone()
            if row:
                data = json.loads(row[0])
                # Use similarity as score (multiplied by 100 for compatibility)
                data['relevance_score'] = int(scores[top_paths.index(file_path)][1] * 100)
                result.append((file_path, scores[top_paths.index(file_path)][1], data))
        conn.close()
        return result
    else:
        # Fallback to keyword scoring if embeddings not available
        conn.close()
        return []
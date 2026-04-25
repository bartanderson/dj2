# world/intent_manager.py
import json
import re
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from world.db import Database

logger = logging.getLogger(__name__)

class IntentManager:
    def __init__(self):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self._conn = None
        self._embedding_dim = 384

    def _get_connection(self):
        return Database.get_connection()

    def _embed(self, text: str) -> List[float]:
        return self.model.encode([text])[0].tolist()

    # ----- Intent CRUD -----
    def add_intent(self, name: str, description: str = "") -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO intents (name, description) VALUES (%s, %s) ON CONFLICT (name) DO NOTHING",
                    (name, description)
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            Database.return_connection(conn)

    def delete_intent(self, name: str) -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM intents WHERE name = %s", (name,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            Database.return_connection(conn)

    def list_intents(self) -> List[Dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, name, description FROM intents ORDER BY name")
                return [{"id": r[0], "name": r[1], "description": r[2]} for r in cur.fetchall()]
        finally:
            Database.return_connection(conn)

    # ----- Example CRUD -----
    def add_example(self, intent_name: str, text: str, is_positive: bool = True) -> bool:
        intent_id = self._get_intent_id(intent_name)
        if not intent_id:
            logger.error(f"Intent '{intent_name}' not found")
            return False
        embedding = self._embed(text)
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO intent_examples (intent_id, example_text, embedding, is_positive) VALUES (%s, %s, %s, %s)",
                    (intent_id, text, embedding, is_positive)
                )
                conn.commit()
                return True
        finally:
            Database.return_connection(conn)

    def update_example(self, example_id: int, new_text: str) -> bool:
        embedding = self._embed(new_text)
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE intent_examples SET example_text = %s, embedding = %s, updated_at = NOW() WHERE id = %s",
                    (new_text, embedding, example_id)
                )
                conn.commit()
                return cur.rowcount > 0
        finally:
            Database.return_connection(conn)

    def delete_example(self, example_id: int) -> bool:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM intent_examples WHERE id = %s", (example_id,))
                conn.commit()
                return cur.rowcount > 0
        finally:
            Database.return_connection(conn)

    def list_examples(self, intent_name: str = None) -> List[Dict]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                if intent_name:
                    cur.execute("""
                        SELECT ie.id, i.name, ie.example_text, ie.is_positive, ie.created_at
                        FROM intent_examples ie
                        JOIN intents i ON ie.intent_id = i.id
                        WHERE i.name = %s
                        ORDER BY ie.id
                    """, (intent_name,))
                else:
                    cur.execute("""
                        SELECT ie.id, i.name, ie.example_text, ie.is_positive, ie.created_at
                        FROM intent_examples ie
                        JOIN intents i ON ie.intent_id = i.id
                        ORDER BY i.name, ie.id
                    """)
                rows = cur.fetchall()
                return [{"id": r[0], "intent": r[1], "text": r[2], "is_positive": r[3], "created_at": r[4]} for r in rows]
        finally:
            Database.return_connection(conn)

    # ----- Rebuild All Embeddings (for model change or initial load) -----
    def rebuild_all_embeddings(self):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, example_text FROM intent_examples")
                rows = cur.fetchall()
                for ex_id, text in rows:
                    embedding = self._embed(text)
                    cur.execute(
                        "UPDATE intent_examples SET embedding = %s, updated_at = NOW() WHERE id = %s",
                        (embedding, ex_id)
                    )
                conn.commit()
                logger.info(f"Rebuilt embeddings for {len(rows)} examples.")
        finally:
            Database.return_connection(conn)

    # ----- Classification -----
    def classify(self, input_text: str, threshold_gap: float = 0.1):
        emb = self._embed(input_text)
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                # Fetch all positive examples
                cur.execute("""
                    SELECT i.name, ie.embedding
                    FROM intent_examples ie
                    JOIN intents i ON ie.intent_id = i.id
                    WHERE ie.is_positive = TRUE
                """)
                rows = cur.fetchall()
                if not rows:
                    return "clarification_needed", 0.0, {}
                best_intent = None
                best_sim = -1
                second_intent = None
                second_sim = -1
                for intent, embedding in rows:
                    # Convert embedding to numpy array if it's a string or list
                    if isinstance(embedding, str):
                        # Parse PostgreSQL vector string like '[0.1,0.2,...]'
                        emb_str = embedding.strip('[]')
                        example_emb = np.array([float(x) for x in emb_str.split(',') if x])
                    elif isinstance(embedding, (list, tuple)):
                        example_emb = np.array(embedding)
                    elif isinstance(embedding, np.ndarray):
                        example_emb = embedding
                    else:
                        print(f"[ERROR] Unexpected embedding type: {type(embedding)}")
                        continue
                    sim = np.dot(emb, example_emb) / (np.linalg.norm(emb) * np.linalg.norm(example_emb))
                    if sim > best_sim:
                        second_intent, second_sim = best_intent, best_sim
                        best_intent, best_sim = intent, sim
                    elif sim > second_sim:
                        second_intent, second_sim = intent, sim
                print(f"[DEBUG] Top intent: {best_intent} ({best_sim:.4f})")
                print(f"[DEBUG] Second intent: {second_intent} ({second_sim:.4f})")
                print(f"[DEBUG] Gap: {best_sim - second_sim:.4f}")
                if best_sim - second_sim < threshold_gap:
                    return "clarification_needed", best_sim, {}
                slots = self._extract_slots(best_intent, input_text)
                return best_intent, best_sim, slots
        finally:
            Database.return_connection(conn)

    def _extract_slots(self, intent: str, text: str) -> dict:
        text_lower = text.lower()
        slots = {}
        if intent == "relocate_self":
            dir_map = {"north": "north", "south": "south", "east": "east", "west": "west",
                       "northeast": "northeast", "northwest": "northwest",
                       "southeast": "southeast", "southwest": "southwest"}
            for word, dir_name in dir_map.items():
                if word in text_lower:
                    slots["destination"] = dir_name
                    break
            if "destination" not in slots:
                match = re.search(r"(?:go|move|walk|travel)\s+(?:to\s+)?(\w+)", text_lower)
                if match:
                    slots["destination"] = match.group(1)
        elif intent in ("acquire_goods", "dispose_goods"):
            match = re.search(r"(?:buy|purchase|get|sell|trade)\s+(?:the\s+)?(\w+(?:\s+\w+)?)", text_lower)
            if match:
                slots["obj"] = match.group(1)
            if "merchant" in text_lower or "trader" in text_lower:
                slots["target"] = "merchant"
            money_match = re.search(r"(\d+)\s*(?:gp|gold|coins?)", text_lower)
            if money_match:
                slots["currency"] = int(money_match.group(1))
        elif intent == "survey_entity":
            match = re.search(r"(?:look at|examine|inspect)\s+(?:the\s+)?(\w+(?:\s+\w+)?)", text_lower)
            if match:
                slots["target"] = match.group(1)
            if "merchant" in text_lower:
                slots["target"] = "merchant"
        elif intent == "negotiate_price":
            match = re.search(r"(?:haggle|negotiate|bargain)\s+(?:on\s+)?(?:the\s+)?(\w+)", text_lower)
            if match:
                slots["obj"] = match.group(1)
            if "merchant" in text_lower:
                slots["target"] = "merchant"
        return slots

    def _get_intent_id(self, name: str) -> Optional[int]:
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM intents WHERE name = %s", (name,))
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            Database.return_connection(conn)

    def clear_examples(self, intent_name: str):
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM intent_examples
                    WHERE intent_id = (SELECT id FROM intents WHERE name = %s)
                """, (intent_name,))
                conn.commit()
        finally:
            Database.return_connection(conn)
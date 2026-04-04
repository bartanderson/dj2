import hashlib
import json
import random
from world.db import Database
from world.dm_chat_ai import get_ai_response

class NameGenerator:
    def __init__(self, world_seed: int, world_theme: str):
        self.world_seed = world_seed
        self.world_theme = world_theme
        self.cache = {}  # in‑memory fallback

    def _get_context_hash(self, region_id, terrain_tags, faction, place_type):
        data = f"{region_id}|{','.join(terrain_tags)}|{faction or ''}|{place_type}"
        return hashlib.md5(data.encode()).hexdigest()

    def _generate_via_ai(self, region_id, terrain_tags, faction, place_type):
        context_hash = self._get_context_hash(region_id, terrain_tags, faction, place_type)
        # Check DB cache
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT name FROM name_cache WHERE world_seed=%s AND region_id=%s AND place_type=%s AND context_hash=%s",
                    (self.world_seed, region_id, place_type, context_hash)
                )
                row = cur.fetchone()
                if row:
                    return row[0]
        finally:
            Database.return_connection(conn)

        # Generate 5 candidate names via AI
        prompt = f"""
You are a fantasy name generator for a {self.world_theme} world.
Region characteristics: {', '.join(terrain_tags)}.
{f"Controlled by {faction}" if faction else ""}
Generate 5 unique names for a {place_type} (e.g., village, dungeon, landmark).
Return ONLY the names, one per line, no extra text.
"""
        response = get_ai_response(prompt, None, {})  # simple call
        names = [line.strip() for line in response.split('\n') if line.strip()]
        if not names:
            # Fallback: generic names
            names = ["New Town", "Old Keep", "Dark Hollow", "Silver Spring", "Grey Rock"]
        # Deterministically pick one using the seed
        rng = random.Random(hash((self.world_seed, region_id, place_type, context_hash)))
        chosen = rng.choice(names)

        # Store in DB
        conn = Database.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO name_cache (world_seed, region_id, place_type, context_hash, name) VALUES (%s, %s, %s, %s, %s)",
                    (self.world_seed, region_id, place_type, context_hash, chosen)
                )
                conn.commit()
        finally:
            Database.return_connection(conn)

        return chosen

    def generate_settlement_name(self, region_id, terrain_tags, faction=None):
        return self._generate_via_ai(region_id, terrain_tags, faction, "settlement")

    def generate_dungeon_name(self, region_id, terrain_tags, danger_level, faction=None):
        return self._generate_via_ai(region_id, terrain_tags, faction, "dungeon")

    def generate_poi_name(self, region_id, terrain_tags, poi_type):
        return self._generate_via_ai(region_id, terrain_tags, None, poi_type)
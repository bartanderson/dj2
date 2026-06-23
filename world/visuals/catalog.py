"""
Asset catalog — SQLite-backed registry of base images, variants, and characters.

Tables:
  base_image  — curated source images (public domain / CC)
  variant     — inpainted variations of a base (season/weather/time/mood)
  character   — cutout character/NPC/enemy sprites
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

CATALOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS base_image (
    id          TEXT PRIMARY KEY,
    path        TEXT NOT NULL,
    source      TEXT,           -- URL or attribution
    license     TEXT,           -- "public_domain", "cc0", "cc_by", etc.
    terrain     TEXT,           -- plains, forest, hills, mountains, desert, coastal, swamp, arctic
    structure   TEXT,           -- wilderness, hut, village, tavern_interior, castle, dungeon
    tags        TEXT,           -- JSON list of descriptive tags
    prompt_hint TEXT            -- prompt fragment to guide inpainting variants
);

CREATE TABLE IF NOT EXISTS variant (
    id          TEXT PRIMARY KEY,
    base_id     TEXT NOT NULL REFERENCES base_image(id),
    path        TEXT NOT NULL,
    season      TEXT,           -- spring, summer, autumn, winter
    weather     TEXT,           -- clear, rain, fog, storm, snow
    time_of_day TEXT,           -- day, dusk, night, dawn
    mood        TEXT,           -- neutral, tense, eerie, cozy, desolate
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS character (
    id          TEXT PRIMARY KEY,
    path        TEXT NOT NULL,  -- PNG with transparency
    char_type   TEXT,           -- npc, enemy, player, creature
    tags        TEXT,           -- JSON list: ["hooded", "merchant", "human"]
    anchor      TEXT            -- JSON {x, y, w, h} placement hint
);
"""


class AssetCatalog:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._conn = sqlite3.connect(str(db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(CATALOG_SCHEMA)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Base images
    # ------------------------------------------------------------------

    def register_base(self, id: str, path: Path, terrain: str, structure: str,
                      source: str = "", license: str = "public_domain",
                      tags: List[str] = None, prompt_hint: str = "") -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO base_image
               (id, path, source, license, terrain, structure, tags, prompt_hint)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, str(path), source, license, terrain, structure,
             json.dumps(tags or []), prompt_hint)
        )
        self._conn.commit()

    def get_base(self, id: str) -> Optional[Dict]:
        row = self._conn.execute(
            "SELECT * FROM base_image WHERE id = ?", (id,)
        ).fetchone()
        return _row_to_dict(row)

    def find_bases(self, terrain: str = None, structure: str = None) -> List[Dict]:
        q = "SELECT * FROM base_image WHERE 1=1"
        params = []
        if terrain:
            q += " AND terrain = ?"
            params.append(terrain)
        if structure:
            q += " AND structure = ?"
            params.append(structure)
        rows = self._conn.execute(q, params).fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Variants
    # ------------------------------------------------------------------

    def register_variant(self, id: str, base_id: str, path: Path,
                         season: str = None, weather: str = None,
                         time_of_day: str = None, mood: str = None) -> None:
        from datetime import datetime, timezone
        self._conn.execute(
            """INSERT OR REPLACE INTO variant
               (id, base_id, path, season, weather, time_of_day, mood, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (id, base_id, str(path), season, weather, time_of_day, mood,
             datetime.now(timezone.utc).isoformat())
        )
        self._conn.commit()

    def find_variant(self, base_id: str, season: str = None, weather: str = None,
                     time_of_day: str = None, mood: str = None) -> Optional[Dict]:
        """Find the closest matching variant for given modifiers."""
        # Exact match first
        q = "SELECT * FROM variant WHERE base_id = ?"
        params = [base_id]
        for col, val in [("season", season), ("weather", weather),
                         ("time_of_day", time_of_day), ("mood", mood)]:
            if val:
                q += f" AND {col} = ?"
                params.append(val)
        row = self._conn.execute(q, params).fetchone()
        if row:
            return _row_to_dict(row)

        # Fallback: any variant for this base
        row = self._conn.execute(
            "SELECT * FROM variant WHERE base_id = ? LIMIT 1", (base_id,)
        ).fetchone()
        return _row_to_dict(row)

    def all_variants_for_base(self, base_id: str) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM variant WHERE base_id = ?", (base_id,)
        ).fetchall()
        return [_row_to_dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Characters
    # ------------------------------------------------------------------

    def register_character(self, id: str, path: Path, char_type: str,
                           tags: List[str] = None, anchor: Dict = None) -> None:
        self._conn.execute(
            """INSERT OR REPLACE INTO character
               (id, path, char_type, tags, anchor)
               VALUES (?, ?, ?, ?, ?)""",
            (id, str(path), char_type, json.dumps(tags or []),
             json.dumps(anchor or {}))
        )
        self._conn.commit()

    def find_characters(self, char_type: str = None, tags: List[str] = None) -> List[Dict]:
        rows = self._conn.execute(
            "SELECT * FROM character" + (" WHERE char_type = ?" if char_type else ""),
            ([char_type] if char_type else [])
        ).fetchall()
        result = [_row_to_dict(r) for r in rows]
        if tags:
            tag_set = set(tags)
            result = [c for c in result
                      if tag_set & set(json.loads(c.get("tags", "[]")))]
        return result

    def close(self):
        self._conn.close()


def _row_to_dict(row) -> Optional[Dict]:
    if row is None:
        return None
    d = dict(row)
    for field in ("tags", "anchor"):
        if field in d and d[field]:
            try:
                d[field] = json.loads(d[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return d

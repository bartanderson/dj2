#!/usr/bin/env python3
"""
Populates PostgreSQL tables from og_system/ design files.
Run after create_tables.py to seed reference data.
"""
import os
import json
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "dungeon_worlds")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

OG_DIR = "og_system"

def connect():
    return psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )

def load_json(filename):
    with open(os.path.join(OG_DIR, filename), "r", encoding="utf-8") as f:
        return json.load(f)

def seed_races(conn):
    data = load_json("03_races.json")  # we haven't seen this file, but we'll assume it's there
    # If missing, we'll skip or load from core?
    # For now, we'll just print a placeholder
    print("Skipping races (03_races.json not yet read)")

def seed_classes(conn):
    # Similar
    print("Skipping classes (02_classes.json not yet read)")

def seed_skills(conn):
    core = load_json("01_core.json")
    skills = core.get("skills", {})
    cur = conn.cursor()
    for skill_name, skill_data in skills.items():
        cur.execute("""
            INSERT INTO skills (name, description, governing_attribute)
            VALUES (%s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                description = EXCLUDED.description,
                governing_attribute = EXCLUDED.governing_attribute
        """, (
            skill_name,
            skill_data.get("covers", [])[0] if skill_data.get("covers") else "",
            "wits"  # default, we can map from core if needed
        ))
    conn.commit()
    print(f"Seeded {len(skills)} skills.")

def seed_spells(conn):
    magic = load_json("04_magic.json")["magic"]
    spells = []
    for school_name, school_data in magic["schools"].items():
        for effect in school_data["effects"]:
            description = effect["description"]
            # Heuristic for stub requirement
            requires_stub = any(kw in description.lower() for kw in ["d6","d8","d10","save","heal","restrain","flee","frightened","poison","grapple","damage","wound","knock"])
            spells.append((
                effect["name"],
                school_name,
                effect.get("cost", school_data["base_cost"]),
                description,
                effect.get("scaling", "None"),
                school_data["tags"],
                requires_stub
            ))
    cur = conn.cursor()
    for spell in spells:
        cur.execute("""
            INSERT INTO spells (name, school, base_cost, description, scaling_text, tags, requires_action_stub)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                school = EXCLUDED.school,
                base_cost = EXCLUDED.base_cost,
                description = EXCLUDED.description,
                scaling_text = EXCLUDED.scaling_text,
                tags = EXCLUDED.tags,
                requires_action_stub = EXCLUDED.requires_action_stub
        """, spell)
    conn.commit()
    print(f"Seeded {len(spells)} spells.")

def main():
    conn = connect()
    try:
        seed_skills(conn)
        seed_spells(conn)
        # seed_races(conn)
        # seed_classes(conn)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
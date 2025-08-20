# create_tables.py
import psycopg2
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "dungeon_worlds")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

def create_database():
    """Create database if it doesn't exist"""
    conn = psycopg2.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        cur.execute(f"CREATE DATABASE {DB_NAME}")
        print(f"Created database: {DB_NAME}")
    except psycopg2.errors.DuplicateDatabase:
        print(f"Database {DB_NAME} already exists")
    finally:
        cur.close()
        conn.close()

def create_tables():
    """Create tables and extensions"""
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    cur = conn.cursor()
    
    # Enable extensions
    extensions = [
        "pg_trgm",   # Text similarity
        "pgcrypto",  # UUID generation
        "vector"     # AI vector search
    ]
    
    for ext in extensions:
        try:
            cur.execute(f"CREATE EXTENSION IF NOT EXISTS {ext}")
            print(f"Enabled extension: {ext}")
        except psycopg2.Error as e:
            print(f"Error enabling {ext}: {e}")
    
    # Create tables
    tables = [
        """
        CREATE TABLE IF NOT EXISTS worlds (
            id SERIAL PRIMARY KEY,
            theme VARCHAR(50) NOT NULL,
            seed INTEGER NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            metadata JSONB
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS players (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            attributes JSONB
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS locations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            type VARCHAR(50) NOT NULL,
            position POINT NOT NULL,
            data JSONB NOT NULL,
            discovered BOOLEAN DEFAULT false
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS quests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            objectives JSONB,
            location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
            completed BOOLEAN DEFAULT false,
            dungeon_required BOOLEAN DEFAULT false
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS factions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            ideology TEXT,
            goals JSONB,
            relationships JSONB,
            activities JSONB
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS npcs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
            location_id UUID REFERENCES locations(id) ON DELETE SET NULL,
            name VARCHAR(100) NOT NULL,
            role VARCHAR(50),
            motivation TEXT,
            dialogue JSONB
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS narrative_context (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,
            player_id UUID REFERENCES players(id) ON DELETE SET NULL,
            timestamp TIMESTAMPTZ DEFAULT NOW(),
            context_type VARCHAR(50) NOT NULL,
            content JSONB NOT NULL,
            embedding VECTOR(1536)
        )
        """
    ]
    
    # Create indexes
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_locations_world ON locations(world_id)",
        "CREATE INDEX IF NOT EXISTS idx_locations_data ON locations USING GIN (data)",
        "CREATE INDEX IF NOT EXISTS idx_quests_world ON quests(world_id)",
        "CREATE INDEX IF NOT EXISTS idx_quests_location ON quests(location_id)",
        "CREATE INDEX IF NOT EXISTS idx_factions_world ON factions(world_id)",
        "CREATE INDEX IF NOT EXISTS idx_npcs_world ON npcs(world_id)",
        "CREATE INDEX IF NOT EXISTS idx_npcs_location ON npcs(location_id)",
        "CREATE INDEX IF NOT EXISTS idx_narrative_world ON narrative_context(world_id)",
        "CREATE INDEX IF NOT EXISTS idx_narrative_player ON narrative_context(player_id)",
        "CREATE INDEX IF NOT EXISTS idx_narrative_timestamp ON narrative_context(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_narrative_embedding ON narrative_context USING ivfflat (embedding)"
    ]
    
    try:
        # Execute table creation
        for table in tables:
            cur.execute(table)
        
        # Execute index creation
        for index in indexes:
            cur.execute(index)
        
        conn.commit()
        print("All tables and indexes created successfully")
    except psycopg2.Error as e:
        print(f"Error creating tables: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    create_database()
    create_tables()
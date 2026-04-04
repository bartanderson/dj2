import psycopg2
from psycopg2.extras import register_uuid
from dotenv import load_dotenv
import os

load_dotenv()
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "dungeon_worlds")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_PORT = os.getenv("DB_PORT", "5432")

def extract_schema():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        port=DB_PORT
    )
    cur = conn.cursor()

    # Get all table names
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
    """)
    tables = [row[0] for row in cur.fetchall()]

    for table in tables:
        print(f"\n=== Table: {table} ===")
        # Get columns
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """, (table,))
        columns = cur.fetchall()
        for col in columns:
            print(f"  {col[0]}: {col[1]} (nullable={col[2]}, default={col[3]})")

        # Get primary key
        cur.execute("""
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu 
                ON tc.constraint_name = kcu.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY' 
              AND tc.table_name = %s;
        """, (table,))
        pk = [row[0] for row in cur.fetchall()]
        if pk:
            print(f"  PRIMARY KEY: {', '.join(pk)}")

        # Get foreign keys
        cur.execute("""
            SELECT
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_name = %s;
        """, (table,))
        fks = cur.fetchall()
        for fk in fks:
            print(f"  FOREIGN KEY: {fk[0]} -> {fk[1]}.{fk[2]}")

        # Get indexes
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = %s;
        """, (table,))
        indexes = cur.fetchall()
        for idx in indexes:
            print(f"  INDEX: {idx[0]} -> {idx[1]}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    extract_schema()
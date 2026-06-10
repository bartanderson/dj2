import sqlite3

DB_PATH = r"C:\Users\bartl\dev\dj2\tools\analysis\engine.db"

def inspect():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # list tables first (sanity check)
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()

    print("\n=== TABLES ===")
    for t in tables:
        print(t[0])

    # check graph_edges existence
    if ("graph_edges",) not in tables:
        print("\nNO graph_edges TABLE FOUND")
        return

    # edge count
    cur.execute("SELECT COUNT(*) FROM graph_edges")
    edge_count = cur.fetchone()[0]

    print("\n=== EDGE COUNT ===")
    print(edge_count)

    # sample rows
    cur.execute("""
        SELECT source_id, target_id, caller, callee, line_number
        FROM graph_edges
        LIMIT 20
    """)
    rows = cur.fetchall()

    print("\n=== SAMPLE EDGES ===")
    for r in rows:
        print(r)

    conn.close()

inspect()
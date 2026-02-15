import sqlite3
conn = sqlite3.connect("ai_context/scout.db")
conn.execute("UPDATE test_patterns SET source_file = 'world/character_builder.py' WHERE extracted_from LIKE '%ref_test_character_builder.py%'")
conn.commit()
conn.close()
print("Patterns updated.")
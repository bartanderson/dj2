import sqlite3; conn=sqlite3.connect('C:_Users_bartl_dev_dj2_tools.old.db'); print(conn.execute("SELECT COUNT(*) FROM symbol_references").fetchone()); 

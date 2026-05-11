import sqlite3
import os

db_path = 'data/app.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN kg_status VARCHAR(32) DEFAULT 'none' NOT NULL")
        conn.commit()
        print("Column kg_status added successfully.")
    except sqlite3.OperationalError as e:
        if "duplicate column name" in str(e):
            print("Column kg_status already exists.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"Database not found at {db_path}")

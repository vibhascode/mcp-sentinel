import os
from app.db import init_db

db_path = "sentinel.db"
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted {db_path}")

init_db()
print("Fresh database initialized.")
from app.db import get_conn

conn = get_conn()
rows = conn.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 5").fetchall()
for row in rows:
    print(dict(row))
conn.close()
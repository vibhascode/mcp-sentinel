import hashlib
import json
from app.db import get_conn

def compute_fingerprint(tool_def: dict) -> str:
    """Hash the parts of a tool definition that matter for behavior."""
    canonical = json.dumps({
        "name": tool_def["name"],
        "description": tool_def["description"],
        "input_schema": tool_def["inputSchema"],
    }, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()

def check_fingerprint(server_name: str, tool_def: dict) -> dict:
    """Returns {'rug_pull': bool, 'is_new': bool}"""
    new_hash = compute_fingerprint(tool_def)
    conn = get_conn()
    row = conn.execute(
        "SELECT fingerprint_hash FROM tool_fingerprints WHERE server_name=? AND tool_name=?",
        (server_name, tool_def["name"])
    ).fetchone()

    if row is None:
        conn.execute(
            "INSERT INTO tool_fingerprints (server_name, tool_name, fingerprint_hash) VALUES (?,?,?)",
            (server_name, tool_def["name"], new_hash)
        )
        conn.commit()
        conn.close()
        return {"rug_pull": False, "is_new": True}

    conn.close()
    return {"rug_pull": row["fingerprint_hash"] != new_hash, "is_new": False}
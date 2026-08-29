import json
import hashlib
from app.db import get_conn

def _content_hash(value) -> str:
    """Deterministic hash of any value — replaces Python's randomized hash()."""
    canonical = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def tag_output(session_id: str, tool_name: str, source_server: str, trust_level: str, output_value) -> str:
    """
    Call this every time a tool call returns data.
    Stores the actual content (for substring matching) plus its hash.
    """
    content_str = str(output_value)
    conn = get_conn()
    conn.execute(
        "INSERT INTO taint_records (session_id, value_ref, source_server, trust_level) VALUES (?, ?, ?, ?)",
        (session_id, content_str, source_server, trust_level)
    )
    conn.commit()
    conn.close()
    return _content_hash(output_value)


def is_tainted(session_id: str, arg_value) -> dict:
    """
    Checks whether arg_value is an exact match to any previously-tagged
    untrusted output in this session.
    Returns {'tainted': bool, 'source_server': str or None}
    """
    conn = get_conn()
    rows = conn.execute(
        "SELECT value_ref, source_server, trust_level FROM taint_records WHERE session_id=?",
        (session_id,)
    ).fetchall()
    conn.close()

    arg_str = str(arg_value)
    for row in rows:
        if row["trust_level"] == "untrusted" and arg_str == row["value_ref"]:
            return {"tainted": True, "source_server": row["source_server"]}

    return {"tainted": False, "source_server": None}

    
def check_taint(session_id: str, tool_name: str, tool_args: dict, privileged_tools: list) -> dict:
    """
    Returns {'blocked': bool, 'reason': str or None}
    Only flags a problem if the target tool is privileged AND an argument is tainted.
    """
    if tool_name not in privileged_tools:
        return {"blocked": False, "reason": None}

    for arg_name, arg_value in tool_args.items():
        result = is_tainted(session_id, arg_value)
        if result["tainted"]:
            return {
                "blocked": True,
                "reason": f"Argument '{arg_name}' traces back to untrusted server '{result['source_server']}'"
            }

    return {"blocked": False, "reason": None}
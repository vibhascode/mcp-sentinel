import json
import re
from app.db import get_conn

# crude keyword-overlap heuristic — works fully offline.
# reka_client.py can later replace score_intent_alignment() with a semantic call.
STOPWORDS = {"the", "a", "an", "to", "for", "of", "my", "me", "please",
             "and", "on", "in", "is", "with", "from", "this", "that"}

def _tokenize(text: str) -> set:
    words = re.split(r"[^a-z0-9]+", text.lower())
    return {w for w in words if w and w not in STOPWORDS and len(w) > 2}


def start_session(session_id: str, original_intent: str):
    """Call once, when the agent's task begins."""
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (session_id, original_intent) VALUES (?, ?)",
        (session_id, original_intent)
    )
    conn.commit()
    conn.close()


def get_original_intent(session_id: str) -> str:
    conn = get_conn()
    row = conn.execute(
        "SELECT original_intent FROM sessions WHERE session_id=?",
        (session_id,)
    ).fetchone()
    conn.close()
    if row is None:
        raise ValueError(f"No session found for session_id={session_id}")
    return row["original_intent"]


def score_intent_alignment(original_intent: str, tool_name: str, tool_args: dict) -> float:
    """
    Returns a 0-1 score for how well this tool call matches the original intent.
    Heuristic: overlap between intent keywords and (tool_name + arg values).
    Swap this out for a Reka Flash semantic call without changing the signature.
    """
    intent_tokens = _tokenize(original_intent)
    if not intent_tokens:
        return 0.0

    action_text = tool_name + " " + " ".join(str(v) for v in tool_args.values())
    action_tokens = _tokenize(action_text)

    if not action_tokens:
        return 0.0

    overlap = intent_tokens & action_tokens
    return len(overlap) / len(intent_tokens)


def check_intent(session_id: str, tool_name: str, tool_args: dict, threshold: float = 0.35) -> dict:
    """Returns {'score': float, 'out_of_scope': bool, 'original_intent': str}"""
    original_intent = get_original_intent(session_id)
    score = score_intent_alignment(original_intent, tool_name, tool_args)
    return {
        "score": score,
        "out_of_scope": score < threshold,
        "original_intent": original_intent,
    }
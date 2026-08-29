from enum import Enum

class Decision(str, Enum):
    ALLOW = "ALLOW"
    ASK_USER = "ASK_USER"
    BLOCK = "BLOCK"


def decide(fingerprint_result: dict, intent_result: dict, taint_result: dict) -> dict:
    """
    Pure function — combines the three independent checks into one decision.

    fingerprint_result: {'rug_pull': bool, 'is_new': bool}
    intent_result:       {'score': float, 'out_of_scope': bool, 'original_intent': str}
    taint_result:        {'blocked': bool, 'reason': str or None}

    Returns: {'decision': Decision, 'reasons': list[str]}
    """
    reasons = []

    # Highest severity first: a tainted value hitting a privileged tool is an
    # active attack in progress — hard block, no exceptions.
    if taint_result["blocked"]:
        reasons.append(taint_result["reason"])
        return {"decision": Decision.BLOCK, "reasons": reasons}

    # A rug pull means the tool you think you're calling is not the tool you
    # last verified — block until a human re-approves the new definition.
    if fingerprint_result["rug_pull"]:
        reasons.append("Tool definition changed since it was last trusted (possible rug pull)")
        return {"decision": Decision.BLOCK, "reasons": reasons}

    # Out-of-scope action: not necessarily malicious, but outside what the
    # user asked for — surface to the user rather than silently blocking.
    if intent_result["out_of_scope"]:
        reasons.append(
            f"Action does not match original intent "
            f"(score={intent_result['score']:.2f}, intent='{intent_result['original_intent']}')"
        )
        return {"decision": Decision.ASK_USER, "reasons": reasons}

    reasons.append("Passed fingerprint, intent, and taint checks")
    return {"decision": Decision.ALLOW, "reasons": reasons}
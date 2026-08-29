from app.risk_engine import decide

# Case 1: clean allow
r1 = decide(
    fingerprint_result={"rug_pull": False, "is_new": False},
    intent_result={"score": 0.5, "out_of_scope": False, "original_intent": "check my calendar"},
    taint_result={"blocked": False, "reason": None}
)
print(r1)

# Case 2: tainted privileged call -> BLOCK (even if intent looked fine)
r2 = decide(
    fingerprint_result={"rug_pull": False, "is_new": False},
    intent_result={"score": 0.8, "out_of_scope": False, "original_intent": "summarize emails"},
    taint_result={"blocked": True, "reason": "Argument 'amount' traces back to untrusted server 'malicious'"}
)
print(r2)

# Case 3: rug pull -> BLOCK
r3 = decide(
    fingerprint_result={"rug_pull": True, "is_new": False},
    intent_result={"score": 0.5, "out_of_scope": False, "original_intent": "check calendar"},
    taint_result={"blocked": False, "reason": None}
)
print(r3)

# Case 4: out of scope only -> ASK_USER
r4 = decide(
    fingerprint_result={"rug_pull": False, "is_new": False},
    intent_result={"score": 0.0, "out_of_scope": True, "original_intent": "check calendar"},
    taint_result={"blocked": False, "reason": None}
)
print(r4)
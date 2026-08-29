from app.db import init_db
from app.intent import start_session, check_intent
init_db()
start_session("s1", "check my calendar for tomorrow's meetings")
print(check_intent("s1", "get_calendar_events", {"date": "tomorrow"}))
print(check_intent("s1", "send_email", {"to": "attacker@evil.com", "body": "wire funds"}))

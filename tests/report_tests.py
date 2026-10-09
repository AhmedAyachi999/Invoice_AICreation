"""Report bot (inv-report-bot): single turnover questions through bot.converse with reports.check_command/answer.
OK = the bot wrote an allowed command with exactly the expected keys and values (no copied example month or year,
no invented period), and Python's final answer contains the expected text. Usage: python tests\\report_tests.py"""
import bot
import reports

ANY_REPORT = {"REPORT_CUSTOMER", "REPORT_PRODUCT", "REPORT_MONTH"}

# (id, message, allowed commands (empty = no command), expected JSON, text the final answer must contain)
CASES = [
    ("R1", "how much turnover did we make with Felix Hartmann in October?", {"REPORT_CUSTOMER"},
     {"name": "Felix Hartmann", "month": 10}, "Felix Hartmann: 92.30"),
    ("R2", "what's our turnover?", ANY_REPORT, {}, "Total: 271.20"),
    ("R3", "turnover per customer from 01/10/2026 to 30/11/2026", {"REPORT_CUSTOMER"},
     {"start": "01/10/2026", "end": "30/11/2026"}, "Total: 271.20"),
    ("R4", "how much did Lena Müller pay us in 2026?", {"REPORT_CUSTOMER"},
     {"name": "Lena Müller", "year": 2026}, "Lena Müller: 113.90"),
    ("R5", "how many USB Cable 1m did we sell in November?", {"REPORT_PRODUCT"},
     {"name": "USB Cable 1m", "month": 11}, "USB Cable 1m: 65.00 (10 sold)"),
    ("R6", "which products sell best?", {"REPORT_PRODUCT"}, {}, "Total: 271.20"),
    ("R7", "give me the turnover month by month for 2026", {"REPORT_MONTH"}, {"year": 2026}, "November: 178.90"),
    ("R8", "monthly turnover of Karl Becker in 2026", {"REPORT_MONTH"},
     {"year": 2026, "customer": "Karl Becker"}, "November: 65.00"),
    ("R9", "what was the turnover of the Desk Lamp in November?", {"REPORT_PRODUCT"},
     {"name": "Desk Lamp", "month": 11}, "Which one do you mean?"),
    ("R10", "how much did we earn with Wanda Kestner?", {"REPORT_CUSTOMER"},
     {"name": "Wanda Kestner"}, "There is no customer called Wanda Kestner."),
    ("R11", "who won the football match yesterday?", set(), {}, "Sorry"),
    ("R12", "delete Karl Becker", set(), {}, ""),
]


def norm(data):
    """Command JSON in a comparable form: empty values dropped, values as lower-case text, 10 == "10"."""
    result = {}
    for key, value in data.items():
        text = "" if value is None else str(value).strip().lower()
        if text:
            result[key] = str(int(text)) if text.isdigit() else text
    return result


real_chat = bot.chat
raw = []
bot.chat = lambda model, messages: raw.append(real_chat(model, messages)) or raw[-1]  # remember the raw reply

score = 0
for case_id, message, allowed, expected, must_contain in CASES:
    result = bot.converse("inv-report-bot", reports.check_command, None, reports.answer, None, message)
    command = bot.parse_command(raw[-1])
    final = result.get("reply") or f"PROPOSAL: {result.get('proposal')}"
    right_command = command[0] in allowed and norm(command[1]) == norm(expected) if command else not allowed
    ok = right_command and must_contain.lower() in final.lower()
    score += ok
    print(f"{case_id}\t{message}\n\tbot:    {raw[-1]}\n\tanswer: {final.replace(chr(10), ' | ')}\n\t"
          f"{'OK' if ok else 'WRONG'}")
print(f"SCORE report\t{score}/{len(CASES)}")

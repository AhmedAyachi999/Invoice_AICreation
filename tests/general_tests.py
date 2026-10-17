"""General test set: customer bot answers, the judge checks it in a loop (until OK, max 3 rounds)."""
import re

from chat import bot

# (id, user message, expected)
#   ("cmd", KEYWORD, {"name": exact, other field: exact (field) or contained (address/value)})
#   ("ask", [words, one must appear])  -> a question, no command
#   ("sorry",)                         -> the Sorry sentence, no command
TESTS = [
    ("G1", "add a new customer", ("ask", ["name"])),
    ("G2", "add customer Nina Vogel", ("ask", ["address"])),
    ("G3", "add customer Nina Vogel, Rosenweg 4, 50667 Köln",
     ("cmd", "CREATE_CUSTOMER", {"name": "nina vogel", "address": "rosenweg 4"})),
    ("G4", "please register Karl Huber, who lives at Bergstr. 9, 80331 München",
     ("cmd", "CREATE_CUSTOMER", {"name": "karl huber", "address": "bergstr. 9"})),
    ("G5", "delete", ("ask", ["which", "who"])),
    ("G6", "delete Karl Huber", ("cmd", "DELETE_CUSTOMER", {"name": "karl huber"})),
    ("G7", "we no longer work with Eva Lang", ("cmd", "DELETE_CUSTOMER", {"name": "eva lang"})),
    ("G8", "change an address", ("ask", ["which", "who"])),
    ("G9", "change the address of Eva Lang", ("ask", ["address"])),
    ("G10", "Eva Lang moved to Parkallee 7, 28209 Bremen",
     ("cmd", "UPDATE_CUSTOMER", {"name": "eva lang", "field": "address", "value": "parkallee 7"})),
    ("G11", "Max Roth is now called Max Roth-Berger",
     ("cmd", "UPDATE_CUSTOMER", {"name": "max roth", "field": "name", "value": "max roth-berger"})),
    ("G12", "rename a customer", ("ask", ["which", "who"])),
    ("G13", "tell me a joke", ("sorry",)),
    ("G14", "what's the weather in Berlin?", ("sorry",)),
    ("G15", "write an invoice for Nina Vogel", ("sorry",)),
]
EXACT = {"name", "field"}
MAX_ROUNDS = 3


def is_correct(answer, expected):
    command = bot.parse_command(answer)
    if expected[0] == "cmd":
        if command is None or command[0] != expected[1]:
            return False
        for key, text in expected[2].items():
            got = str(command[1].get(key, "")).strip().lower()
            if (got != text) if key in EXACT else (text not in got):
                return False
        return True
    if command is not None:
        return False
    if expected[0] == "sorry":
        return "only help with customers" in answer.lower()
    return "?" in answer and any(w in answer.lower() for w in expected[1])


def judge(message, answer):
    text = bot.chat("inv-judge-bot", [{"role": "user", "content": f"User message: {message}\nAssistant answer: {answer}"}])
    m = re.search(r"Message to the assistant:\s*(.*)", text, re.S)
    return (m.group(1) if m else text).strip().replace("\n", " ")


for tid, message, expected in TESTS:
    history = [{"role": "user", "content": message}]
    answer = bot.chat("inv-customer-bot", history).strip()
    first, steps = answer, []
    for _ in range(MAX_ROUNDS):
        feedback = judge(message, answer)
        steps.append(feedback)
        if feedback.upper().startswith("OK"):
            break
        history += [{"role": "assistant", "content": answer},
                    {"role": "user", "content": f"Correction from the checker: {feedback} Give your corrected answer to my previous message."}]
        answer = bot.chat("inv-customer-bot", history).strip()
        steps.append("-> " + answer.replace("\n", " | "))
    rounds = sum(1 for s in steps if s.startswith("-> "))
    ok = lambda a: "correct" if is_correct(a, expected) else "wrong"
    print("\t".join([tid, message, first.replace("\n", " | "), ok(first), " || ".join(steps), str(rounds), ok(answer)]))

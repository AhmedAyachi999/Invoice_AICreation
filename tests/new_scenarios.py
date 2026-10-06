"""15 new scenarios: customer bot answers, Python checks the answer against the expected result, the judge judges it."""
import re

import bot

# (id, user message, expected) - expected is one of:
#   ("cmd", KEYWORD, {field: text that must be contained (lower case)})
#   ("ask", [words, one of them must appear])       -> a question, no command
#   ("sorry",)                                      -> the off-topic sentence, no command
SCENARIOS = [
    ("N1", "Could you please take Helmut Schmidt off the books?", ("cmd", "DELETE_CUSTOMER", {"name": "helmut schmidt"})),
    ("N2", "The customer Maria Lopez has a new address: Alexanderplatz 1, 10178 Berlin",
     ("cmd", "UPDATE_CUSTOMER", {"name": "maria", "field": "address", "value": "alexanderplatz 1"})),
    ("N3", "Small typo: Wilfried's name is spelled Wilfried Bäcker",
     ("cmd", "UPDATE_CUSTOMER", {"name": "wilfried", "field": "name", "value": "wilfried bäcker"})),
    ("N4", "I'd like to onboard a new customer", ("ask", ["name"])),
    ("N5", "onboard Jonas Meyer", ("ask", ["address"])),
    ("N6", "New customer Lukas Brandt, living at Gartenweg 12, 45127 Essen",
     ("cmd", "CREATE_CUSTOMER", {"name": "lukas brandt", "address": "gartenweg 12"})),
    ("N7", "Tell me a joke", ("sorry",)),
    ("N8", "Please update the address of Helmut Wagner", ("ask", ["address"])),
    ("N9", "delete", ("ask", ["which", "who", "name"])),
    ("N10", "Helmut Wagner closed the business, please remove that customer",
     ("cmd", "DELETE_CUSTOMER", {"name": "helmut wagner"})),
    ("N11", "Maria Lopez's correct address is Torstr. 14, 10119 Berlin, not 12",
     ("cmd", "UPDATE_CUSTOMER", {"name": "maria", "field": "address", "value": "torstr. 14"})),
    ("N12", "Send an email to Wilfried", ("sorry",)),
    ("N13", "Add customer: name = Sophie Wolf; address = Am Markt 3, 53111 Bonn",
     ("cmd", "CREATE_CUSTOMER", {"name": "sophie wolf", "address": "am markt 3"})),
    ("N14", "Rename customer Anna Klein to Anna Klein-Schulz",
     ("cmd", "UPDATE_CUSTOMER", {"name": "anna klein", "field": "name", "value": "anna klein-schulz"})),
    ("N15", "What's the capital of France?", ("sorry",)),
]


def is_correct(answer, expected):
    command = bot.parse_command(answer)
    if expected[0] == "cmd":
        if command is None or command[0] != expected[1]:
            return False
        return all(text in str(command[1].get(field, "")).lower() for field, text in expected[2].items())
    if command is not None:
        return False
    if expected[0] == "sorry":
        return "only help with customers" in answer.lower()
    return "?" in answer and any(w in answer.lower() for w in expected[1])


def describe(expected):
    if expected[0] == "cmd":
        return f"{expected[1]} " + ", ".join(f"{k}~{v}" for k, v in expected[2].items())
    return "asks (" + "/".join(expected[1]) + ")" if expected[0] == "ask" else "Sorry sentence"


for sid, message, expected in SCENARIOS:
    answer = bot.chat("inv-customer-bot", [{"role": "user", "content": message}]).strip()
    judged = bot.chat("inv-judge-bot", [{"role": "user", "content": f"User message: {message}\nAssistant answer: {answer}"}])
    verdict = re.search(r"4\.\s*Verdict:\s*(\w+)", judged)
    reason = re.search(r"4\.\s*Verdict:\s*(.*)", judged)
    print("\t".join([sid, message, describe(expected), answer.replace("\n", " | "),
                     "correct" if is_correct(answer, expected) else "wrong",
                     verdict.group(1).upper() if verdict else "?", (reason.group(1) if reason else judged[-150:]).strip()]))

"""20 fresh scenarios (new names, new wording), customer bot WITHOUT judge. Usage: python fresh_tests.py <model>"""
import sys
from pathlib import Path

exec((Path(__file__).parent / "general_tests.py").read_text(encoding="utf-8").split("TESTS = [")[0])  # bot, re
exec("def _src():\n    pass")  # placeholder so the next exec keeps definitions
src = (Path(__file__).parent / "general_tests.py").read_text(encoding="utf-8")
exec(src[src.index("EXACT = "):src.index("def judge(")])  # EXACT, MAX_ROUNDS, is_correct (strict name check)

TESTS = [
    ("H1", "I want to create a customer record", ("ask", ["name"])),
    ("H2", "new client: Greta Lindner", ("ask", ["address"])),
    ("H3", "create Greta Lindner, Hafenweg 3, 20457 Hamburg",
     ("cmd", "CREATE_CUSTOMER", {"name": "greta lindner", "address": "hafenweg 3"})),
    ("H4", "Felix Hartmann's address is Lindenallee 12, 04109 Leipzig, please add this customer",
     ("cmd", "CREATE_CUSTOMER", {"name": "felix hartmann", "address": "lindenallee 12"})),
    ("H5", "remove a customer", ("ask", ["which", "who"])),
    ("H6", "remove Ida Sommer from the customer list", ("cmd", "DELETE_CUSTOMER", {"name": "ida sommer"})),
    ("H7", "Leon Krüger is not our customer anymore", ("cmd", "DELETE_CUSTOMER", {"name": "leon krüger"})),
    ("H8", "I want to edit a customer", ("ask", ["which", "who"])),
    ("H9", "update Oskar Brandl's address", ("ask", ["address"])),
    ("H10", "Oskar Brandl's new address is Domplatz 5, 93047 Regensburg",
     ("cmd", "UPDATE_CUSTOMER", {"name": "oskar brandl", "field": "address", "value": "domplatz 5"})),
    ("H11", "Ida Sommer relocated to Seeufer 8, 88131 Lindau",
     ("cmd", "UPDATE_CUSTOMER", {"name": "ida sommer", "field": "address", "value": "seeufer 8"})),
    ("H12", "Greta Lindner is now Greta Lindner-Wolf",
     ("cmd", "UPDATE_CUSTOMER", {"name": "greta lindner", "field": "name", "value": "greta lindner-wolf"})),
    ("H13", "please fix the spelling: Felix Hartman should be Felix Hartmann",
     ("cmd", "UPDATE_CUSTOMER", {"name": "felix hartman", "field": "name", "value": "felix hartmann"})),
    ("H14", "change a name", ("ask", ["which", "who"])),
    ("H15", "recommend a good restaurant", ("sorry",)),
    ("H16", "how much does Leon Krüger owe us?", ("sorry",)),
    ("H17", "create an invoice for Ida Sommer", ("sorry",)),
    ("H18", "translate hello into French", ("sorry",)),
    ("H19", "add", ("ask", ["name", "what", "which"])),
    ("H20", "delete the customer", ("ask", ["which", "who"])),
]

model = sys.argv[1]
score = 0
for tid, message, expected in TESTS:
    answer = bot.chat(model, [{"role": "user", "content": message}]).strip()
    ok = is_correct(answer, expected)
    score += ok
    print("\t".join([tid, message, answer.replace("\n", " | "), "correct" if ok else "wrong"]))
print(f"SCORE\t{score}/{len(TESTS)}")

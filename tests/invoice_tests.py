"""20 single-message scenarios for the invoice bot (bot alone). Usage: python invoice_tests.py [model]"""
import sys

from chat import bot

# (id, user message, expected)
#   ("cmd", KEYWORD, {field: expected})  texts exact (lower case); "lines": list of (product, quantity, unit_price or None)
#   ("ask", [words, one must appear])    -> a question, no command
#   ("sorry",)                           -> the Sorry sentence, no command
TESTS = [
    ("V1", "I need a new invoice", ("ask", ["customer", "who"])),
    ("V2", "make an invoice for Bruno Seidel", ("ask", ["date"])),
    ("V3", "invoice for Bruno Seidel dated 12/10/2026, due 11/11/2026", ("ask", ["line", "product", "what"])),
    ("V4", "invoice for Bruno Seidel, date 12/10/2026, due date 11/11/2026, 4 Desk Fan, unpaid",
     ("cmd", "CREATE_INVOICE", {"customer": "bruno seidel", "date": "12/10/2026", "due_date": "11/11/2026",
                                "status": "unpaid", "lines": [("desk fan", 4, None)]})),
    ("V5", "bill Carla Neumann: 2 Laptop at 850 and 5 Mouse, date 03/10/2026, due 02/11/2026, status unpaid",
     ("cmd", "CREATE_INVOICE", {"customer": "carla neumann", "date": "03/10/2026", "due_date": "02/11/2026",
                                "status": "unpaid", "lines": [("laptop", 2, 850), ("mouse", 5, None)]})),
    ("V6", "Dieter Vogt bought 10 Notebook A5 on 01/09/2026, payable by 15/09/2026, already paid",
     ("cmd", "CREATE_INVOICE", {"customer": "dieter vogt", "date": "01/09/2026", "due_date": "15/09/2026",
                                "status": "paid", "lines": [("notebook a5", 10, None)]})),
    ("V7", "new invoice for Emma Kraft, 20/10/2026 to 19/11/2026, 1 Standing Desk, 2 Desk Lamp and 3 Pen Set, unpaid",
     ("cmd", "CREATE_INVOICE", {"customer": "emma kraft", "date": "20/10/2026", "due_date": "19/11/2026",
                                "status": "unpaid",
                                "lines": [("standing desk", 1, None), ("desk lamp", 2, None), ("pen set", 3, None)]})),
    ("V8", "invoice for Emma Kraft, 20/10/2026, due 19/11/2026, 2 Desk Lamp", ("ask", ["paid", "status"])),
    ("V9", "INV-007 was paid",
     ("cmd", "UPDATE_INVOICE", {"id": "inv-007", "field": "status", "value": "paid"})),
    ("V10", "set invoice INV-012 back to unpaid",
     ("cmd", "UPDATE_INVOICE", {"id": "inv-012", "field": "status", "value": "unpaid"})),
    ("V11", "the due date of INV-003 is now 30/11/2026",
     ("cmd", "UPDATE_INVOICE", {"id": "inv-003", "field": "due_date", "value": "30/11/2026"})),
    ("V12", "change the date of invoice INV-005 to 02/10/2026",
     ("cmd", "UPDATE_INVOICE", {"id": "inv-005", "field": "date", "value": "02/10/2026"})),
    ("V13", "mark an invoice as paid", ("ask", ["which", "number"])),
    ("V14", "delete invoice INV-009", ("cmd", "DELETE_INVOICE", {"id": "inv-009"})),
    ("V15", "remove an invoice", ("ask", ["which", "number"])),
    ("V16", "INV-002 was created by mistake, please delete it", ("cmd", "DELETE_INVOICE", {"id": "inv-002"})),
    ("V17", "what is the best football team?", ("sorry",)),
    ("V18", "how do I bake bread?", ("sorry",)),
    ("V19", "write a poem about the sea", ("sorry",)),
    ("V20", "invoice", ("ask", ["customer", "who"])),
]
EXACT = {"customer", "date", "due_date", "status", "id", "field", "value"}


def same_number(got, expected):
    try:
        return abs(float(str(got).replace(",", ".")) - expected) < 0.001
    except ValueError:
        return False


def same_lines(got, expected):
    if not isinstance(got, list) or len(got) != len(expected):
        return False
    for line, (product, quantity, price) in zip(got, expected):
        if not isinstance(line, dict) or str(line.get("product", "")).strip().lower() != product:
            return False
        if not same_number(line.get("quantity"), quantity):
            return False
        if price is None and line.get("unit_price") not in (None, ""):
            return False
        if price is not None and not same_number(line.get("unit_price"), price):
            return False
    return True


def is_correct(answer, expected):
    command = bot.parse_command(answer)
    if expected[0] == "cmd":
        if command is None or command[0] != expected[1]:
            return False
        for key, want in expected[2].items():
            got = command[1].get(key, "")
            if key == "lines":
                if not same_lines(got, want):
                    return False
            elif str(got).strip().lower() != want:
                return False
        return True
    if command is not None:
        return False
    if expected[0] == "sorry":
        return "only help with invoices" in answer.lower()
    return "?" in answer and any(w in answer.lower() for w in expected[1])


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "inv-invoice-bot"
    score = 0
    for tid, message, expected in TESTS:
        answer = bot.chat(model, [{"role": "user", "content": message}]).strip()
        ok = is_correct(answer, expected)
        score += ok
        print("\t".join([tid, message, answer.replace("\n", " | "), "correct" if ok else "wrong"]))
    print(f"SCORE\t{score}/{len(TESTS)}")

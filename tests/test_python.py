"""Evaluation: the bots alone (A, PYTHON off) vs the bots with Python's corrections and forms (B, PYTHON on, the
website as it is). With PYTHON off there are no forms and no Python checks: the bot's raw command goes straight to
answer()/build_proposal(); an exception there counts as end not correct. RUNS = 1.
The simulated user answers whatever the bot asks, like a real user, from the case's answer maps:
"forms" {ui: what static/app.js sends} and "typed" [(keywords in the question, typed answer)], first match wins,
else "default". A types every answer. B sends the form when a mapped form opens (again and again if asked again),
and types when the bot asks without a form. Asking again is fine; only the measured end result counts.
Each run: a fresh database copy, a new conversation."""
import re
import time

import helpers  # first: points the database to a temporary copy
import api  # noqa: E402
from chat import assistant, bot  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

STRICT = TestClient(api.app)  # POST /chat like the website, but an app exception comes back as itself (not HTTP 500)
RUNS = 1
MAX_MESSAGES = 6  # per run: the first message + the answers / forms
ASKS = ("please enter", "please write", "again")  # a request to the user, also without "?"
NEW_ADDRESS = "Bahnhofstr. 1, 53111 Bonn"
PICKER = f"invoice date {helpers.day(0)}, due date {helpers.day(14)}"  # the date picker allows no past invoice date
KARL = ("PUT", "/customers/CUS-008", {"name": "Karl Becker", "address": NEW_ADDRESS})
DELETE_TIM = ("DELETE", "/customers/CUS-012", None)  # Tim Wagner has no invoices
PAID_004 = ("PUT", "/invoices/INV-004", {"customer_id": "CUS-003", "date": "01/10/2026", "due_date": "31/10/2026",
                                         "status": "paid"})
TEA_CUP = ("POST", "/products", {"name": "Tea Cup", "sell_price": 4.5})


def new_invoice(date, due, quantity):
    """The expected POST /invoices proposal: Karl Becker, unpaid, one line quantity x Desk Lamp."""
    return ("POST", "/invoices", {"customer_id": "CUS-008", "date": date, "due_date": due, "status": "unpaid",
                                  "lines": [{"product_id": "PRD-001", "quantity": quantity, "unit_price": 29.9}]})


def customer_maps(name):
    """Choose an existing customer: the chooser, or the typed name."""
    return {"forms": {"customer": f"customer: {name}"}, "typed": [(["customer", "which", "name"], name)], "default": name}


def invoice_maps(lines):
    """A new invoice for Karl Becker dated 20/10/2026, due 31/10/2026, unpaid (B's date picker: today, today + 14)."""
    dates = "invoice date 20/10/2026, due date 31/10/2026"
    return {"forms": {"customer": "customer: Karl Becker", "dates": PICKER, "lines": f"products: {lines}",
                      "status": "unpaid"},
            "typed": [(["paid or unpaid", "status"], "unpaid"), (["date"], dates), (["customer", "who"], "Karl Becker"),
                      (["product", "quantit", "line", "item"], lines)], "default": dates}


INVOICE_004 = {"forms": {"invoice": "INV-004", "status": "paid"},
               "typed": [(["invoice number", "which invoice", "number"], "INV-004"), (["paid or unpaid", "status"], "paid")],
               "default": "INV-004"}
TEA_CUP_MAPS = {"forms": {"new_product": "new product Tea Cup, sell price 4.50"},
                "typed": [(["negative"], "add product Tea Cup, price 4.50"), (["price"], "4.50"), (["name"], "Tea Cup")]}

# id, kind, first message, answer maps (forms, typed, default); expected end: proposal (method, path, body fields;
# body None = no body), proposal_b (B may also end with the date picker's dates), or report (numbers of reports.py)
CASES = [
    {"id": "1", "kind": "control", "message": f"change the address of Karl Becker to {NEW_ADDRESS}",
     "forms": {"customer": "customer: Karl Becker"},
     "typed": [(["customer", "which", "name"], "Karl Becker"), (["address"], NEW_ADDRESS)], "default": "Karl Becker",
     "proposal": KARL},
    {"id": "2", "kind": "tricky", "message": f"change the customer's address to {NEW_ADDRESS}",
     "forms": {"customer": "customer: Karl Becker"},
     "typed": [(["customer", "which", "name"], "Karl Becker"), (["address"], NEW_ADDRESS)], "default": "Karl Becker",
     "proposal": KARL},
    {"id": "3", "kind": "turnover", "message": "turnover per month 2026",
     "forms": {"monthly_turnover": "monthly turnover for 2026, all customers, all products"},
     "typed": [(["year"], "2026"), (["customer"], "all customers"), (["product"], "all products")], "default": "2026",
     "report": {"kind": "months", "year": "2026"}},
    # tricky: the first message misses something or has a wrong value
    {"id": "4", "kind": "tricky", "message": "delete the customer", **customer_maps("Tim Wagner"), "proposal": DELETE_TIM},
    {"id": "5", "kind": "tricky", "message": "remove the product",  # Office Chair is in no invoice
     "forms": {"product": "product: Office Chair"}, "typed": [(["product", "which", "name"], "Office Chair")],
     "default": "Office Chair", "proposal": ("DELETE", "/products/PRD-003", None)},
    {"id": "6", "kind": "tricky", "message": "mark the invoice as paid", **INVOICE_004, "proposal": PAID_004},
    {"id": "7", "kind": "tricky", "message": "add product Tea Cup, price -4.50", **TEA_CUP_MAPS,
     "default": "add product Tea Cup, price 4.50", "proposal": TEA_CUP},
    {"id": "8", "kind": "tricky", "message": "add product Tea Cup", **TEA_CUP_MAPS, "default": "4.50",
     "proposal": TEA_CUP},
    {"id": "9", "kind": "tricky",
     "message": "new invoice for Karl Becker dated 20/10/2026, 2 Desk Lamp, due 31/02/2026, unpaid",
     **invoice_maps("2 Desk Lamp"), "proposal": new_invoice("20/10/2026", "31/10/2026", 2),
     "proposal_b": new_invoice(helpers.day(0), helpers.day(14), 2)},
    {"id": "10", "kind": "tricky",
     "message": "new invoice for Nobody Smith dated 20/10/2026, 1 Desk Lamp, due 31/10/2026, unpaid",
     **invoice_maps("1 Desk Lamp"), "default": "Karl Becker", "proposal": new_invoice("20/10/2026", "31/10/2026", 1),
     "proposal_b": new_invoice(helpers.day(0), helpers.day(14), 1)},
    {"id": "11", "kind": "tricky",
     "message": "invoice for Karl Becker dated 20/10/2026 with 3 Flying Carpet, due 31/10/2026, unpaid",
     **invoice_maps("3 Desk Lamp"), "default": "3 Desk Lamp", "proposal": new_invoice("20/10/2026", "31/10/2026", 3),
     "proposal_b": new_invoice(helpers.day(0), helpers.day(14), 3)},
    {"id": "12", "kind": "tricky", "message": "change the Desk Lamp price to abc",
     "forms": {"edit_product": "product: Desk Lamp, new sell price 30.00", "product": "product: Desk Lamp"},
     "typed": [(["price", "number"], "30.00"), (["product", "which"], "Desk Lamp")], "default": "30.00",
     "proposal": ("PUT", "/products/PRD-001", {"name": "Desk Lamp", "sell_price": 30.0})},
    {"id": "13", "kind": "tricky", "message": "delete customer CUS-999", **customer_maps("Tim Wagner"),
     "proposal": DELETE_TIM},
    {"id": "14", "kind": "tricky", "message": "add a customer named Lena Berg",
     "forms": {"new_customer": "add customer Lena Berg, Ringstr. 2, 44135 Dortmund"},
     "typed": [(["address"], "Ringstr. 2, 44135 Dortmund"), (["name"], "Lena Berg")],
     "default": "Ringstr. 2, 44135 Dortmund",
     "proposal": ("POST", "/customers", {"name": "Lena Berg", "address": "Ringstr. 2, 44135 Dortmund"})},
    # control: valid requests (a mapped form may still open: asking again is allowed)
    {"id": "15", "kind": "control", "message": "add a new customer Lena Hoffmann, Gartenweg 5, 44137 Dortmund",
     "forms": {"new_customer": "add customer Lena Hoffmann, Gartenweg 5, 44137 Dortmund"},
     "typed": [(["address"], "Gartenweg 5, 44137 Dortmund"), (["name"], "Lena Hoffmann")],
     "default": "Gartenweg 5, 44137 Dortmund",
     "proposal": ("POST", "/customers", {"name": "Lena Hoffmann", "address": "Gartenweg 5, 44137 Dortmund"})},
    {"id": "16", "kind": "control", "message": "add a product",
     "forms": {"new_product": "new product USB-3 Cable, sell price 9.90"},
     "typed": [(["price"], "9.90"), (["name"], "USB-3 Cable")], "default": "USB-3 Cable",
     "proposal": ("POST", "/products", {"name": "USB-3 Cable", "sell_price": 9.9})},
    {"id": "17", "kind": "control", "message": "mark invoice INV-004 as paid", **INVOICE_004, "proposal": PAID_004},
    {"id": "18", "kind": "control", "message": "delete the customer Tim Wagner", **customer_maps("Tim Wagner"),
     "proposal": DELETE_TIM},
    # turnover
    {"id": "19", "kind": "turnover", "message": "turnover by customer for October 2026",
     "forms": {"turnover": "turnover per customer from 01/10/2026 to 31/10/2026, all customers"},
     "typed": [(["date", "period", "from", "when", "month"], "from 01/10/2026 to 31/10/2026"),
               (["customer"], "all customers")], "default": "from 01/10/2026 to 31/10/2026",
     "report": {"kind": "customers", "start": "01/10/2026", "end": "31/10/2026"}},
    {"id": "20", "kind": "turnover", "message": "turnover of the Desk Lamp in 2026",
     "forms": {"product_turnover": "turnover per product from 01/01/2026 to 31/12/2026, product: Desk Lamp (PRD-001)"},
     "typed": [(["date", "period", "from", "when", "year"], "from 01/01/2026 to 31/12/2026"),
               (["product"], "Desk Lamp")], "default": "from 01/01/2026 to 31/12/2026",
     "report": {"kind": "products", "start": "01/01/2026", "end": "31/12/2026", "id": "PRD-001"}},
]


def set_python(on):
    """Switch Python's corrections and forms: assistant.py has its own copy (from chat.bot import PYTHON), so set both."""
    bot.PYTHON = assistant.PYTHON = on


def send(log, cid, message):
    """One message to POST /chat like the website; the raw exchange goes into log.
    An exception in the app (bot alone: build_proposal/answer on bad data) comes back as {"error": text}."""
    started = time.time()
    try:
        response = STRICT.post("/chat", json={"message": message, "conversation_id": cid})
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") \
            else {"reply": response.text}
        status = f"HTTP {response.status_code}"
    except Exception as exc:
        data, status = {"error": f"{type(exc).__name__}: {exc}"}, "EXCEPTION"
    log.append(f">>> {message}\n    {status}, {time.time() - started:.1f} s, "
               f"entity={data.get('entity')}\n    reply: {data.get('reply')!r}\n    ui: {data.get('ui')}\n"
               f"    proposal: {data.get('proposal')}" + (f"\n    exception: {data['error']}" if "error" in data else ""))
    return data


AMOUNT = re.compile(r"\d+(?:[.,]\d{3})*[.,]\d{2}(?!\d)")  # 59.80, 59,80, 1,500.00, 1.500,00


def amounts(text):
    """All amounts in a text as 2-decimal numbers (the last . or , is the decimal point)."""
    return {round(float(re.sub(r"[.,]", "", a[:-3]) + "." + a[-2:]), 2) for a in AMOUNT.findall(text)}


def report_match(text, report):
    """The numbers of reports.py in the reply: every non-zero row amount and the total (wording, names, order
    and rows with 0 don't matter)."""
    if report["kind"] == "months":
        rows = [r["turnover"] for r in helpers.get(f"/reports/months?year={report['year']}")]
    else:
        rows = [r["turnover"] for r in helpers.get(f"/reports/{report['kind']}?start={report['start']}"
                                                   f"&end={report['end']}")
                if report.get("id") in (None, r.get("customer_id"), r.get("product_id"))]
    expected = {round(t, 2) for t in rows if t} | {round(sum(rows), 2)}
    return expected <= amounts(text)


def proposal_match(p, expected):
    """Method, path and the expected body fields (body None = no body)."""
    method, path, body = expected
    right_body = p.get("body") is None if body is None else \
        isinstance(p.get("body"), dict) and all(p["body"].get(k) == v for k, v in body.items())
    return p.get("method") == method and p.get("path") == path and right_body


def end_correct(case, data, forms):
    """The expected end: the right proposal, or a reply with reports.py's numbers. B may also end with proposal_b."""
    if "report" in case:
        return not data.get("proposal") and report_match(data.get("reply") or "", case["report"])
    expected = [case["proposal"]] + ([case["proposal_b"]] if forms and "proposal_b" in case else [])
    return any(proposal_match(data.get("proposal") or {}, e) for e in expected)


def asks(data):
    """The bot asks or requests something: open, a "?", or "please enter/write ... again". "Sorry, I can only" is not."""
    text = (data.get("reply") or "").lower()
    if text.startswith("sorry, i can only"):
        return False
    return bool(data.get("open")) or "?" in text or any(word in text for word in ASKS)


def typed_answer(case, data):
    """The first typed answer whose keywords are in the bot's question, else the case's default."""
    text = (data.get("reply") or "").lower()
    return next((answer for words, answer in case["typed"] if any(w in text for w in words)), case.get("default"))


def run_case(case, forms, log):
    """One run in one mode. Returns (form correct or None in A, end correct)."""
    shown = set()
    data = send(log, None, case["message"])
    for _ in range(MAX_MESSAGES - 1):
        if "error" in data:
            return (shown <= set(case["forms"]) if forms else None), False  # an exception: end not correct
        if end_correct(case, data, forms) or data.get("proposal"):
            break  # the end: the expected result, or a (wrong) proposal
        ui = data.get("ui") or []  # A: router.converse shows no forms
        shown |= set(ui)
        form = next((u for u in ui if u in case["forms"]), None)
        if form:
            data = send(log, data.get("conversation_id"), case["forms"][form])  # the form, also again
        elif ui:
            break  # a form, but none of this task's forms
        elif asks(data) and typed_answer(case, data):
            data = send(log, data.get("conversation_id"), typed_answer(case, data))
        else:
            break  # a final answer, "Sorry, I can only ...", or nothing to answer
    form_ok = shown <= set(case["forms"]) if forms else None  # every form that appeared belongs to the task
    return form_ok, "error" not in data and end_correct(case, data, forms)


if __name__ == "__main__":
    rows, shown = [], []
    try:
        for case in CASES:
            row = {"case": f"{case['id']} {case['kind']}: {case['message']}", "A": [], "B form": [], "B": []}
            for forms in (False, True):
                set_python(forms)
                mode = "B bot + Python" if forms else "A bot alone"
                for number in range(1, RUNS + 1):
                    helpers.fresh_db()
                    log = []
                    form_ok, end_ok = run_case(case, forms, log)
                    if forms:
                        row["B form"].append(form_ok)
                        row["B"].append(end_ok)
                    else:
                        row["A"].append(end_ok)
                    print(f"case {case['id']} {mode} run {number}: form correct {form_ok}, end correct {end_ok}")
                    if not end_ok or form_ok is False:
                        shown.append(f"===== case {case['id']} ({case['kind']}), {mode}, run {number}: "
                                     f"form correct {form_ok}, end correct {end_ok} =====\n" + "\n".join(log))
            rows.append(row)
    finally:
        set_python(True)

    count = lambda values: f"{sum(bool(v) for v in values)}/{RUNS}"  # noqa: E731
    table = ["| case | A bot alone end correct | B bot + Python form correct | B bot + Python end correct |",
             "|---|---|---|---|"]
    table += [f"| {r['case']} | {count(r['A'])} | {count(r['B form'])} | {count(r['B'])} |" for r in rows]
    total = len(CASES) * RUNS
    summary = [f"A bot alone: end correct {sum(sum(map(bool, r['A'])) for r in rows)}/{total}",
               f"B bot + Python: form correct {sum(sum(map(bool, r['B form'])) for r in rows)}/{total}, "
               f"end correct {sum(sum(map(bool, r['B'])) for r in rows)}/{total}"]

    print("\n\n##### Raw exchange of every non-expected run\n")
    print("\n\n".join(shown) or "(none)")
    print("\n##### Results\n")
    print("\n".join(table + [""] + summary))

    file = helpers.ROOT / "tests" / "results" / f"{helpers.TODAY.isoformat()}_python.md"
    file.write_text(f"# Bot alone vs bot + Python {helpers.TODAY.isoformat()}\n\nA = bot alone (PYTHON off: no "
                    f"forms, no Python checks or corrections), B = bot + Python (the website as it is). POST /chat on a temporary copy of data/invoices.db, {RUNS} run(s) per "
                    f"case and mode, a new conversation each run.\n\n" + "\n".join(table) + "\n\n" +
                    "\n\n".join(summary) + "\n\n## Raw exchange of every non-expected run\n\n" +
                    ("\n\n".join(f"```\n{s}\n```" for s in shown) or "(none)") + "\n", encoding="utf-8")
    print(f"\nResults written to {file}")

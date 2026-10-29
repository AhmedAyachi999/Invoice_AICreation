"""Answers must match the database: 11a, 11b, 11c, 11d, 12, 12b, 17 (bot scenarios, 5 runs each)."""
import calendar
import re

import helpers  # first: points the database to a temporary copy

RUNS = 5


def scenario_11a(run):
    """"is INV-011 paid?": says paid/unpaid exactly as in the database."""
    status = helpers.get("/invoices/INV-011")["status"]
    data = run.say("is INV-011 paid?")
    text = (data.get("reply") or "").lower()
    unpaid = "unpaid" in text or "not paid" in text
    run.useful(data)
    run.check(f"reply says {status}", (unpaid if status == "unpaid" else "paid" in text and not unpaid))
    return run.done()


def scenario_11b(run):
    """"how many invoices are paid?": the right number appears in the reply."""
    count = sum(i["status"] == "paid" for i in helpers.get("/invoices"))
    data = run.say("how many invoices are paid?")
    run.useful(data)
    run.check(f"the number {count} is in the reply", re.search(rf"\b{count}\b", data.get("reply") or ""))
    return run.done()


def scenario_11c(run):
    """"how much does the kettle cost?": names only products that exist, or asks which one.
    Checked: no example product name from the modelfiles / assistant.SYSTEM is in the reply."""
    data = run.say("how much does the kettle cost?")
    run.useful(data)
    text = data.get("reply") or ""
    invented = [name for name in helpers.example_names() if name.lower() in text.lower()]
    run.check(f"no example name in the reply {invented}", not invented)
    return run.done()


def scenario_11d(run):
    """"where does Karl Becker live?" and "what does the Desk Lamp cost?": address and price as in the database."""
    address = helpers.get("/customers/CUS-008")["address"]
    price = helpers.get("/products/PRD-001")["sell_price"]
    data = run.say("where does Karl Becker live?")
    run.useful(data)
    run.check(f"address {address!r} in the reply", address in (data.get("reply") or ""))
    data = run.say("what does the Desk Lamp cost?")
    run.useful(data)
    run.check(f"price {price:.2f} in the reply", re.search(rf"\b{price:.2f}\b|\b{price}\b".replace(".", r"[.,]"),
                                                           data.get("reply") or ""))
    return run.done()


PERIODS = [("01/01/2026", "31/12/2026"), ("01/10/2026", "31/10/2026")]
YEARS = ["2026", "2025"]


def form(run, question, ui, message):
    """Ask a turnover question; if the form opens, send the form's message. Returns the reply text."""
    data = run.say(question)
    if not run.check(f"form '{ui}' opens", ui in (data.get("ui") or [])):
        return ""
    data = run.say(message)
    run.useful(data)
    return data.get("reply") or ""


def same_numbers(run, text, rows, label):
    """Every row of reports.py (name and turnover) and the total are in the reply."""
    total = sum(row["turnover"] for row in rows)
    missing = [f"{row[label]} {row['turnover']:.2f}" for row in rows if f"{row[label]} {row['turnover']:.2f}" not in text]
    run.check(f"same numbers as reports.py (missing: {missing}), total {total:.2f}",
              not missing and f"total {total:.2f}" in text)


def scenario_12(run):
    """The three turnover forms, as app.js sends them, several periods: same numbers as core/reports.py."""
    for start, end in PERIODS:
        rows = helpers.get(f"/reports/customers?start={start}&end={end}")
        text = form(run, "show me the turnover per customer", "turnover",
                    f"turnover per customer from {start} to {end}, all customers")
        same_numbers(run, text, rows, "name")
        rows = helpers.get(f"/reports/products?start={start}&end={end}")
        text = form(run, "show me the turnover per product", "product_turnover",
                    f"turnover per product from {start} to {end}, all products")
        same_numbers(run, text, rows, "name")
    for year in YEARS:
        rows = [{"month": calendar.month_name[r["month"]], "turnover": r["turnover"]}
                for r in helpers.get(f"/reports/months?year={year}")]
        text = form(run, "show me the monthly turnover", "monthly_turnover",
                    f"monthly turnover for {year}, all customers, all products")
        same_numbers(run, text, rows, "month")
    return run.done()


def scenario_12b(run):
    """Turnover per customer form with a name that doesn't exist, and with one of two customers of the same name:
    an error or the right customer, never all customers. FAIL if any other customer's row is in the reply."""
    dup = helpers.client.post("/customers", json={"name": "Karl Becker", "address": "Am Markt 7, 04109 Leipzig"}).json()
    helpers.client.post("/invoices", json={"customer_id": dup["id"], "date": "01/06/2026", "due_date": "15/06/2026",
                                           "status": "paid", "lines": [{"product_id": "PRD-001", "quantity": 3}]})
    period = "from 01/01/2026 to 31/12/2026"
    rows = helpers.get("/reports/customers?start=01/01/2026&end=31/12/2026")
    for name, cid in [("Nobody Known", "CUS-999"), ("Karl Becker", dup["id"])]:
        text = form(run, "show me the turnover per customer", "turnover",
                    f"turnover per customer {period}, customer: {name} ({cid})")
        others = [f"{r['name']} {r['turnover']:.2f}" for r in rows if r["customer_id"] != cid
                  and f"{r['name']} {r['turnover']:.2f}" in text]
        run.check(f"{name} ({cid}): no other customer's turnover in the reply {others}", not others)
    return run.done()


BUTTON = re.compile(  # "click the X button", "press X", "the X button"
    r'(?:click|press)(?: on)? (?:the )?"?([\w ]+?)"?(?: button\b|[.,;]|$)|the "?([\w ]+?)"? button', re.I)


CANNOT = "I cannot help with that."


def scenario_17(run):
    """Help: a function that doesn't exist gets "I cannot help with that."; real functions asked in other words
    ("bill", "client", "sales") get a real answer; no invented button."""
    guide = (helpers.ROOT / "docs" / "user_guide.md").read_text(encoding="utf-8").lower()  # a button must be in here
    for question in ["can I export to Excel?", "how do I remove a bill?", "how do I add a client?",
                     "where can I see my sales?"]:
        response = helpers.client.post("/help", json={"message": question, "conversation_id": None})
        reply = response.json().get("reply", "")
        run.out(f">>> /help {question}\n    HTTP {response.status_code}\n    reply: {reply!r}")
        answer = reply.split("\n\nFrom the user guide:")[0]
        buttons = [(a or b).strip().lower() for a, b in BUTTON.findall(answer)]
        run.check(f"no invented button {buttons}", all(button in guide for button in buttons))
        if "export" in question:
            run.check(f'"{CANNOT}"', answer.strip() == CANNOT)
        else:
            run.check(f'a real answer, not "{CANNOT}"', CANNOT not in answer)
        if "bill" in question:
            run.check('delete steps: "delete an invoice" (or "remove an invoice", the chat understands both) and Yes',
                      ("delete an invoice" in answer.lower() or "remove an invoice" in answer.lower())
                      and "yes" in answer.lower())
        if "client" in question:
            run.check('"add a customer"', "add a customer" in answer.lower())
    return run.done()


if __name__ == "__main__":
    for number, function in [("11a", scenario_11a), ("11b", scenario_11b), ("11c", scenario_11c),
                             ("11d", scenario_11d), ("12", scenario_12), ("12b", scenario_12b), ("17", scenario_17)]:
        helpers.repeat(number, function, RUNS)

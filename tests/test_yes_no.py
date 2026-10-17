"""Yes / No scenarios 2, 3, 4, 5, 7, 22 (bot scenarios, 5 runs each)."""
import re

import helpers  # first: points the database to a temporary copy
import test_customer_lifecycle
import test_invoice_lifecycle

RUNS = 5
NEW = "add a new customer Lena Hoffmann, Gartenweg 5, 44137 Dortmund"
CLAIM = re.compile(r"\b(saved|done|has been (changed|updated)|was (changed|updated)|is now)\b", re.I)


def scenario_2(run):
    """Create, change and delete a customer, but click No each time: the database stays the same."""
    start = helpers.snapshot()
    for message in [NEW, "change the address of Tim Wagner to Hafenstr. 9, 20457 Hamburg", "delete the customer Tim Wagner"]:
        data, _ = run.follow(run.say(message), {"customer": "customer: Tim Wagner"})
        run.useful(data)
        run.out("    (No: the proposal is not sent)")
        run.check("database unchanged", helpers.snapshot() == start)
    return run.done()


def summary_matches(run, proposal, saved):
    """Every value in the proposal's summary = the saved value (for a delete: the record before)."""
    s, products = proposal["summary"], {p["id"]: p["name"] for p in helpers.get("/products")}
    patterns = [
        (r"Create customer: (.*) \| (.*)", lambda m: [m[1] == saved["name"], m[2] == saved["address"]]),
        (r"Change (\w+) of (CUS-\d+) \(.*\): '.*' -> '(.*)'", lambda m: [m[2] == saved["id"], m[3] == saved[m[1]]]),
        (r"Delete customer (CUS-\d+): (.*) \| (.*)",
         lambda m: [m[1] == saved["id"], m[2] == saved["name"], m[3] == saved["address"]]),
        (r"Create invoice for (CUS-\d+) \(.*\) \| date (\S+) \| due (\S+) \| (\w+) \| (.*) \| total ([\d.]+)",
         lambda m: [m[1] == saved["customer_id"], m[2] == saved["date"], m[3] == saved["due_date"],
                    m[4] == saved["status"], m[6] == f"{saved['total']:.2f}", lines_match(m[5], saved, products)]),
        (r"Change (\w+) of (INV-\d+): '.*' -> '(.*)'", lambda m: [m[2] == saved["id"], m[3] == saved[m[1]]]),
        (r"Delete invoice (INV-\d+) \((CUS-\d+), (\S+), (\w+)\) \| total ([\d.]+)",
         lambda m: [m[1] == saved["id"], m[2] == saved["customer_id"], m[3] == saved["date"],
                    m[4] == saved["status"], m[5] == f"{saved['total']:.2f}"]),
    ]
    for pattern, compare in patterns:
        match = re.fullmatch(pattern, s)
        if match:
            return run.check(f"summary = saved: {s!r} vs {saved}", all(compare(match)))
    return run.check(f"summary in a known format: {s!r}", False)


def lines_match(text, saved, products):
    """'1: 2 x Desk Lamp x 29.90 = 59.80; ...' = the saved lines."""
    found = re.findall(r"(\d+): (\d+) x (.+?) x ([\d.]+) = ([\d.]+)", text)
    expected = [(str(l["line"]), str(l["quantity"]), products[l["product_id"]], f"{l['unit_price']:.2f}",
                 f"{l['quantity'] * l['unit_price']:.2f}") for l in saved["lines"]]
    return found == expected


def scenario_3(run):
    """For 1a and 1b: each proposal's summary = what is saved after Yes."""
    pairs = test_customer_lifecycle.run_once(run) + test_invoice_lifecycle.run_once(run)
    run.check("6 proposals (3 customer, 3 invoice)", len(pairs) == 6)
    for proposal, saved in pairs:
        if saved:
            summary_matches(run, proposal, saved)
    return run.done()


def scenario_4(run):
    """Tim Wagner and Tim Weber exist; "delete Tim Wagner" -> Yes: only Tim Wagner is gone."""
    helpers.client.post("/customers", json={"name": "Tim Weber", "address": "Lindenweg 4, 50667 Köln"})
    before = helpers.get("/customers")
    wagner = next(c for c in before if c["name"] == "Tim Wagner")
    data, _ = run.follow(run.say("delete Tim Wagner"), {"customer": "customer: Tim Wagner"})
    if run.check("a proposal is shown", data.get("proposal")):
        run.check("database unchanged before Yes", helpers.get("/customers") == before)
        run.yes(data["proposal"])
        run.check("only Tim Wagner is gone", helpers.get("/customers") == [c for c in before if c != wagner])
    return run.done()


def scenario_5(run):
    """A proposal to change an address; the customer is deleted meanwhile; the old proposal -> 404, nothing created."""
    data, _ = run.follow(run.say("change the address of Tim Wagner to Hafenstr. 9, 20457 Hamburg"),
                         {"customer": "customer: Tim Wagner"})
    if run.check("a proposal is shown", data.get("proposal")):
        wagner = next(c for c in helpers.get("/customers") if c["name"] == "Tim Wagner")
        run.out(f">>> DELETE /customers/{wagner['id']}: HTTP {helpers.client.delete('/customers/' + wagner['id']).status_code}")
        after_delete = helpers.snapshot()
        response = run.yes(data["proposal"])
        run.check("refused with 404", response.status_code == 404)
        run.check("nothing created or changed", helpers.snapshot() == after_delete)
    return run.done()


def scenario_7(run):
    """Change Karl Becker's address: no 'saved/done' without a proposal; the database changes only after Yes."""
    new = "Bahnhofstr. 1, 53111 Bonn"
    before = helpers.snapshot()
    data, replies = run.follow(run.say(f"change the address of Karl Becker to {new}"),
                               {"customer": "customer: Karl Becker"})
    for reply in replies:
        if not reply.get("proposal"):
            run.useful(reply)
            run.check("reply does not say saved/done", not CLAIM.search(reply.get("reply") or ""))
    run.check("database unchanged before Yes", helpers.snapshot() == before)
    if run.check("a proposal is shown", data.get("proposal")):
        run.yes(data["proposal"])
        run.check("after Yes: Karl Becker has the new address", helpers.get("/customers/CUS-008")["address"] == new)
    return run.done()


def scenario_22(run):
    """Delete a paid invoice through the chat: refused, no proposal."""
    before = helpers.snapshot()
    run.check("precondition: INV-011 is paid", helpers.get("/invoices/INV-011")["status"] == "paid")
    data = run.say("delete invoice INV-011")
    run.useful(data)
    run.check("no proposal", not data.get("proposal"))
    run.check("database unchanged", helpers.snapshot() == before)
    return run.done()


if __name__ == "__main__":
    for number, function in [("2", scenario_2), ("3", scenario_3), ("4", scenario_4), ("5", scenario_5),
                             ("7", scenario_7), ("22", scenario_22)]:
        helpers.repeat(number, function, RUNS)

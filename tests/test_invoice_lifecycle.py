"""Scenario 1b - Invoice: create, change, delete through the chat, each confirmed with Yes.
Uses Karl Becker (CUS-008) and the Desk Lamp (PRD-001) from the database copy."""
import helpers  # first: points the database to a temporary copy

CUSTOMER, CUSTOMER_ID = "Karl Becker", "CUS-008"
PRODUCT, PRODUCT_ID, QUANTITY = "Desk Lamp", "PRD-001", 2
DATE, DUE, NEW_DUE = helpers.day(0), helpers.day(14), helpers.day(30)
FILL = {"customer": f"customer: {CUSTOMER}", "product": f"product: {PRODUCT}",  # the messages app.js sends
        "dates": f"invoice date {DATE}, due date {DUE}", "lines": f"products: {QUANTITY} {PRODUCT}",
        "status": "unpaid"}


def step(run, message, fill):
    """Send a message, fill the forms, check the database is unchanged before Yes, then say Yes."""
    before = helpers.snapshot()
    data, _ = run.follow(run.say(message), fill)
    if not run.check("a proposal is shown", data.get("proposal")):
        return None, None
    run.check("database unchanged before Yes", helpers.snapshot() == before)
    return data["proposal"], run.yes(data["proposal"])


def run_once(run):
    """The three steps; returns the list of (proposal, saved record) for scenario 3."""
    pairs = []
    start = helpers.get("/invoices")
    # 1. Create
    proposal, response = step(run, f"create a new invoice for {CUSTOMER} with {QUANTITY} {PRODUCT}", FILL)
    if proposal is None:
        return pairs
    new_id = response.json().get("id", "") if response.status_code == 201 else ""
    saved = helpers.get(f"/invoices/{new_id}") if new_id else None
    run.check("new number INV-...", new_id.startswith("INV-") and all(i["id"] != new_id for i in start))
    run.check(f"customer = {CUSTOMER_ID}", saved and saved["customer_id"] == CUSTOMER_ID)
    run.check(f"one line: {QUANTITY} x {PRODUCT_ID}", saved and [(l["product_id"], l["quantity"]) for l in
                                                                   saved["lines"]] == [(PRODUCT_ID, QUANTITY)])
    run.check("status = unpaid", saved and saved["status"] == "unpaid")
    pairs.append((proposal, saved))
    if not saved:
        return pairs
    # 2. Change the due date
    proposal, response = step(run, f"change the due date of {new_id} to {NEW_DUE}", {"invoice": new_id})
    if proposal is None:
        return pairs
    changed = helpers.get(f"/invoices/{new_id}")
    run.check(f"{new_id} due_date = {NEW_DUE}", changed and changed["due_date"] == NEW_DUE)
    run.check(f"{new_id} everything else unchanged", changed and {**changed, "due_date": NEW_DUE} ==
              {**saved, "due_date": NEW_DUE})
    pairs.append((proposal, changed))
    # 3. Delete
    proposal, response = step(run, f"delete invoice {new_id}", {"invoice": new_id})
    if proposal is None:
        return pairs
    run.check(f"{new_id} no longer exists", helpers.get(f"/invoices/{new_id}") is None)
    pairs.append((proposal, changed))  # for a delete: the record as it was before
    run.check("same invoices as before the test", helpers.get("/invoices") == start)
    return pairs


def scenario_1b(run):
    run_once(run)
    return run.done()


if __name__ == "__main__":
    helpers.repeat("1b", scenario_1b, 5)

"""Scenario 1a - Customer: create, change, delete through the chat, each confirmed with Yes."""
import helpers  # first: points the database to a temporary copy

NAME, ADDRESS = "Lena Hoffmann", "Gartenweg 5, 44137 Dortmund"
NEW_ADDRESS = "Hafenstr. 9, 20457 Hamburg"
FILL = {"new_customer": f"add customer {NAME}, {ADDRESS}", "customer": f"customer: {NAME}"}


def step(run, message):
    """Send a message, fill the forms, check the database is unchanged before Yes, then say Yes.
    Returns (proposal, response) or (None, None) if no proposal came."""
    before = helpers.snapshot()
    data, _ = run.follow(run.say(message), FILL)
    if not run.check("a proposal is shown", data.get("proposal")):
        return None, None
    run.check("database unchanged before Yes", helpers.snapshot() == before)
    return data["proposal"], run.yes(data["proposal"])


def run_once(run):
    """The three steps; returns the list of (proposal, saved record) for scenario 3."""
    pairs = []
    start = helpers.get("/customers")
    run.check("precondition: the name is not in the database", all(c["name"] != NAME for c in start))
    # 1. Create
    proposal, response = step(run, f"add a new customer {NAME}, {ADDRESS}")
    if proposal is None:
        return pairs
    new_id = response.json().get("id", "") if response.status_code == 201 else ""
    saved = helpers.get(f"/customers/{new_id}") if new_id else None
    run.check("new number CUS-...", new_id.startswith("CUS-") and all(c["id"] != new_id for c in start))
    run.check(f"name = {NAME!r}", saved and saved["name"] == NAME)
    run.check(f"address = {ADDRESS!r}", saved and saved["address"] == ADDRESS)
    pairs.append((proposal, saved))
    if not saved:
        return pairs
    # 2. Change the address
    proposal, response = step(run, f"change the address of {NAME} to {NEW_ADDRESS}")
    if proposal is None:
        return pairs
    changed = helpers.get(f"/customers/{new_id}")
    run.check(f"{new_id} address = {NEW_ADDRESS!r}", changed and changed["address"] == NEW_ADDRESS)
    run.check(f"{new_id} name unchanged", changed and changed["name"] == NAME)
    pairs.append((proposal, changed))
    # 3. Delete
    proposal, response = step(run, f"delete the customer {NAME}")
    if proposal is None:
        return pairs
    run.check(f"{new_id} no longer exists", helpers.get(f"/customers/{new_id}") is None)
    pairs.append((proposal, changed))  # for a delete: the record as it was before
    run.check("same customers as before the test", helpers.get("/customers") == start)
    return pairs


def scenario_1a(run):
    run_once(run)
    return run.done()


if __name__ == "__main__":
    helpers.repeat("1a", scenario_1a, 5)

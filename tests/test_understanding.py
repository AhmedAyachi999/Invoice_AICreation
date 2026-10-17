"""Understanding: 13a-13e (bot scenarios, 5 runs each)."""
import helpers  # first: points the database to a temporary copy

RUNS = 5


def routed(run, message, entity):
    """Send one message; the reply must come from the expected bot."""
    data = run.say(message)
    run.useful(data)
    run.check(f"entity = {entity}", data.get("entity") == entity)
    return run.done()


def asks_which(run, message, kind, forms):
    """Send one message; the bot asks which record or shows a form, and no example name is in the reply."""
    data = run.say(message)
    run.useful(data)
    text = (data.get("reply") or "").lower()
    run.check(f"asks which {kind} or shows a form {forms}", f"which {kind}" in text or set(forms) & set(data.get("ui") or []))
    invented = [name for name in helpers.example_names() if name.lower() in text]
    run.check(f"no example name in the reply {invented}", not invented)
    return run.done()


def scenario_13a(run):
    return routed(run, "add a customer named Lena Berg", "customer")


def scenario_13b(run):
    return routed(run, "INV-004 is paid", "invoice")


def scenario_13c(run):
    run.check("precondition: Tim Wagner exists", any(c["name"] == "Tim Wagner" for c in helpers.get("/customers")))
    return routed(run, "remove Tim Wagner", "customer")


def scenario_13d(run):
    return asks_which(run, "change the price", "product", ["product", "edit_product"])


def scenario_13e(run):
    return asks_which(run, "update the address", "customer", ["customer"])


if __name__ == "__main__":
    for number, function in [("13a", scenario_13a), ("13b", scenario_13b), ("13c", scenario_13c),
                             ("13d", scenario_13d), ("13e", scenario_13e)]:
        helpers.repeat(number, function, RUNS)

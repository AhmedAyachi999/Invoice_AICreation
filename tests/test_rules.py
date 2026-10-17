"""Accounting rules 8, 8b, 9, 10, 10b, 22b, 23b, 24, 26. All Python only (1 run), except 10b (chat, 5 runs)."""
import helpers  # first: points the database to a temporary copy

client = helpers.client


def call(run, method, path, body=None):
    """One CRUD call, printed."""
    response = client.request(method, path, json=body) if body is not None else client.request(method, path)
    run.out(f">>> {method} {path} {body if body is not None else ''}\n    HTTP {response.status_code}: {response.text}")
    return response


def invoice(customer="CUS-008", date="17/10/2026", due="31/10/2026", status="unpaid", lines=None):
    """An invoice body for POST /invoices."""
    return {"customer_id": customer, "date": date, "due_date": due, "status": status,
            "lines": lines or [{"product_id": "PRD-001", "quantity": 1}]}


def scenario_8(run):
    """DELETE a paid invoice: HTTP 400, invoice still there."""
    run.check("precondition: INV-011 is paid", helpers.get("/invoices/INV-011")["status"] == "paid")
    run.check("HTTP 400", call(run, "DELETE", "/invoices/INV-011").status_code == 400)
    run.check("INV-011 still there", helpers.get("/invoices/INV-011") is not None)
    return run.done()


def scenario_8b(run):
    """PUT the paid invoice to unpaid, then DELETE it: print what happens."""
    old = helpers.get("/invoices/INV-011")
    body = {**{k: old[k] for k in ("customer_id", "date", "due_date", "lines")}, "status": "unpaid"}
    put = call(run, "PUT", "/invoices/INV-011", body).status_code
    delete = call(run, "DELETE", "/invoices/INV-011").status_code
    observed = f"PUT {put}, DELETE {delete}, INV-011 exists afterwards: {helpers.get('/invoices/INV-011') is not None}"
    run.out("OBSERVED: " + observed)
    return run.done(observed)


def scenario_9(run):
    """Create an invoice, delete it, create another: print both numbers."""
    first = call(run, "POST", "/invoices", invoice()).json()["id"]
    call(run, "DELETE", f"/invoices/{first}")
    second = call(run, "POST", "/invoices", invoice()).json()["id"]
    run.out(f"OBSERVED: first {first}, second {second}")
    return run.done(f"first {first}, second {second}")


def scenario_10(run):
    """Wrong data through the CRUD endpoints: each refused (4xx), nothing saved."""
    start = helpers.snapshot()
    for name, method, path, body in [
            ("product with sell price -5", "POST", "/products", {"name": "Bad Product", "sell_price": -5}),
            ("invoice line with quantity 0", "POST", "/invoices", invoice(lines=[{"product_id": "PRD-001", "quantity": 0}])),
            ("invoice with date 31/02/2026", "POST", "/invoices", invoice(date="31/02/2026", due="31/03/2026")),
            ("due date before the invoice date", "POST", "/invoices", invoice(date="17/10/2026", due="10/10/2026"))]:
        run.check(f"{name}: refused (4xx)", 400 <= call(run, method, path, body).status_code < 500)
        run.check(f"{name}: nothing saved", helpers.snapshot() == start)
    return run.done()


def scenario_10b(run):
    """Through the chat: "add a product" -> form USB-3 Cable, 9.90 -> Yes: proposal shown and saved."""
    before = helpers.snapshot()
    data, _ = run.follow(run.say("add a product"), {"new_product": "new product USB-3 Cable, sell price 9.90"})
    if run.check("a proposal is shown", data.get("proposal")):
        run.check("database unchanged before Yes", helpers.snapshot() == before)
        response = run.yes(data["proposal"])
        saved = helpers.get(f"/products/{response.json().get('id')}") if response.status_code == 201 else None
        run.check("saved: USB-3 Cable, sell price 9.9", saved and saved["name"] == "USB-3 Cable"
                  and saved["sell_price"] == 9.9)
    return run.done()


def scenario_22b(run):
    """Change the Desk Lamp's price: an old invoice keeps the old unit price, a new invoice uses the new one."""
    old = next(i for i in helpers.get("/invoices") if any(l["product_id"] == "PRD-001" for l in i["lines"]))
    lamp = helpers.get("/products/PRD-001")
    call(run, "PUT", "/products/PRD-001", {"name": lamp["name"], "sell_price": 35.0})
    run.check(f"{old['id']} keeps its unit prices", helpers.get(f"/invoices/{old['id']}") == old)
    new = call(run, "POST", "/invoices", invoice()).json()["id"]
    run.check(f"{new} uses the new price 35.0", helpers.get(f"/invoices/{new}")["lines"][0]["unit_price"] == 35.0)
    return run.done()


def scenario_23b(run):
    """3 x 0.10 and 7 x 19.99: total 140.23 exactly."""
    cheap = call(run, "POST", "/products", {"name": "Test Item Ten Cent", "sell_price": 0.10}).json()["id"]
    dear = call(run, "POST", "/products", {"name": "Test Item 19.99", "sell_price": 19.99}).json()["id"]
    new = call(run, "POST", "/invoices", invoice(lines=[{"product_id": cheap, "quantity": 3},
                                                         {"product_id": dear, "quantity": 7}])).json()["id"]
    response = client.get(f"/invoices/{new}")
    run.out(f">>> GET /invoices/{new}\n    {response.text}")
    run.check("total is exactly 140.23 in the answer", '"total":140.23}' in response.text)
    run.out("NOT TESTED: line totals 0.30 / 139.93 - the API returns no line total, only quantity and unit_price")
    return run.done()


def scenario_24(run):
    """Paid invoices due on the start date, on the end date, one day after the end: first two counted, third not."""
    customer = call(run, "POST", "/customers", {"name": "Test Range Customer", "address": "Ring 1, 10115 Berlin"}).json()["id"]
    for due, quantity in [("01/01/2027", 1), ("31/01/2027", 10), ("01/02/2027", 100)]:  # Desk Lamp 29.90 each
        call(run, "POST", "/invoices", invoice(customer, due, due, "paid", [{"product_id": "PRD-001", "quantity": quantity}]))
    response = client.get("/reports/customers", params={"start": "01/01/2027", "end": "31/01/2027"})
    run.out(f">>> GET /reports/customers 01/01/2027-31/01/2027\n    {response.text}")
    row = next((r for r in response.json() if r["customer_id"] == customer), {})
    run.check("turnover = 11 x 29.90 = 328.9 (first two only)", row.get("turnover") == 328.9)
    return run.done()


def scenario_26(run):
    """Invoice for a missing customer, line with a missing product, quantity -1: each refused, nothing saved."""
    start = helpers.snapshot()
    for name, body in [("customer CUS-999", invoice(customer="CUS-999")),
                       ("product PRD-999", invoice(lines=[{"product_id": "PRD-999", "quantity": 1}])),
                       ("quantity -1", invoice(lines=[{"product_id": "PRD-001", "quantity": -1}]))]:
        run.check(f"{name}: refused (4xx)", 400 <= call(run, "POST", "/invoices", body).status_code < 500)
        run.check(f"{name}: nothing saved", helpers.snapshot() == start)
    return run.done()


if __name__ == "__main__":
    for number, function in [("8", scenario_8), ("8b", scenario_8b), ("9", scenario_9), ("10", scenario_10),
                             ("22b", scenario_22b), ("23b", scenario_23b), ("24", scenario_24), ("26", scenario_26)]:
        helpers.repeat(number, function, 1)
    helpers.repeat("10b", scenario_10b, 5)

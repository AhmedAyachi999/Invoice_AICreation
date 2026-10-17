from datetime import datetime

from core import storage
from entities import customers, products

STATUSES = ["paid", "unpaid"]
FIELDS = ["date", "due_date", "status"]


def invoice_total(invoice):
    """Sum of quantity x unit_price over all lines, rounded to the cent."""
    return round(sum(line["quantity"] * line["unit_price"] for line in invoice["lines"]), 2)


def to_date(text):
    """Turn a DD/MM/YYYY text into a date, or None if it is not a valid date."""
    try:
        return datetime.strptime(str(text).strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


def to_quantity(value):
    """Turn a quantity into a whole number > 0, or None if it is not one."""
    try:
        number = float(str(value).strip().replace(",", "."))
    except ValueError:
        return None
    return int(number) if number == int(number) and number > 0 else None


def check_invoice(invoice):
    """Return an error message if customer, dates, status or lines are not valid, else None."""
    if storage.find(storage.load("customers"), invoice.get("customer_id")) is None:
        return f"There is no customer {invoice.get('customer_id')}."
    for field in ["date", "due_date"]:
        if to_date(invoice.get(field)) is None:
            return f"The {field} must be a valid date DD/MM/YYYY, not '{invoice.get(field)}'."
    if to_date(invoice["due_date"]) < to_date(invoice["date"]):
        return "The due_date must not be before the date."
    if str(invoice.get("status", "")).strip().lower() not in STATUSES:
        return "The status must be paid or unpaid."
    lines = invoice.get("lines")
    if not isinstance(lines, list) or not lines:
        return "The invoice needs at least one line."
    all_products = storage.load("products")
    for number, line in enumerate(lines, start=1):
        if storage.find(all_products, line.get("product_id")) is None:
            return f"Line {number}: there is no product {line.get('product_id')}."
        if to_quantity(line.get("quantity")) is None:
            return f"Line {number}: the quantity must be a whole number greater than 0."
        price = line.get("unit_price")
        if price is not None and str(price).strip() != "":
            error = products.check_product({"name": "line", "sell_price": price})
            if error:
                return f"Line {number}: " + error.replace("sell_price", "unit_price")
    return None


def make_lines(lines):
    """Number the lines 1, 2, 3...; the unit_price defaults to the product's sell_price."""
    all_products = storage.load("products")
    result = []
    for number, line in enumerate(lines, start=1):
        price = products.to_price(line.get("unit_price"))
        if price is None:
            price = storage.find(all_products, line["product_id"])["sell_price"]
        result.append({"line": number, "product_id": line["product_id"],
                       "quantity": to_quantity(line["quantity"]), "unit_price": price})
    return result


def create_invoice(data):
    """Give the invoice the next number, save it and return it."""
    invoices = storage.load("invoices")
    invoice = {"id": storage.next_id("invoices", invoices), "customer_id": data["customer_id"],
               "date": data["date"].strip(), "due_date": data["due_date"].strip(),
               "status": data["status"].strip().lower(), "lines": make_lines(data["lines"])}
    invoices.append(invoice)
    storage.save("invoices", invoices)
    return invoice


def update_invoice(invoice_id, data):
    """Replace customer, dates, status and lines of an invoice; return it, or None if the number doesn't exist."""
    invoices = storage.load("invoices")
    invoice = storage.find(invoices, invoice_id)
    if invoice is None:
        return None
    invoice["customer_id"] = data["customer_id"]
    invoice["date"] = data["date"].strip()
    invoice["due_date"] = data["due_date"].strip()
    invoice["status"] = data["status"].strip().lower()
    invoice["lines"] = make_lines(data["lines"])
    storage.save("invoices", invoices)
    return invoice


def delete_invoice(invoice_id):
    """Delete an invoice; return it, None if the number doesn't exist, ValueError if it is paid."""
    invoices = storage.load("invoices")
    invoice = storage.find(invoices, invoice_id)
    if invoice is None:
        return None
    if invoice["status"] == "paid":
        raise ValueError(f"Invoice {invoice_id} cannot be deleted: it is paid.")
    invoices.remove(invoice)
    storage.save("invoices", invoices)
    return invoice


def find_one(found, kind, name):
    """Return (record, None) if exactly one record was found, else (None, a message for the user)."""
    if not found:
        return None, f"There is no {kind} called {name}."
    if len(found) > 1:
        return None, f"There are {len(found)} {kind}s called {name}: " \
                     f"{', '.join(r['name'] for r in found)}. Which one do you mean?"
    return found[0], None


def resolve(data):
    """Turn a CREATE_INVOICE command with names into invoice data with numbers. Return (data, error message)."""
    customer, error = find_one(customers.find_customers(data.get("customer", "")), "customer", data.get("customer"))
    if error:
        return None, error
    lines = data.get("lines")
    if not isinstance(lines, list) or not lines:
        return None, "The invoice needs at least one line."
    resolved = []
    for line in lines:
        if not isinstance(line, dict):
            return None, "Each line needs a product and a quantity."
        product, error = find_one(products.find_products(line.get("product", "")), "product", line.get("product"))
        if error:
            return None, error
        resolved.append({"product_id": product["id"], "quantity": line.get("quantity"),
                         "unit_price": line.get("unit_price")})
    return {"customer_id": customer["id"], "date": str(data.get("date", "")),
            "due_date": str(data.get("due_date", "")), "status": str(data.get("status", "")),
            "lines": resolved}, None


def changed_invoice(data):
    """For UPDATE_INVOICE: the invoice data of the record with the one field changed, or None if it doesn't exist."""
    invoice = storage.find(storage.load("invoices"), str(data.get("id", "")).strip().upper())
    if invoice is None:
        return None
    return {**invoice, data.get("field"): str(data.get("value", "")).strip()}


def check_command(command, data):
    """Check a command of the invoice bot. Return an error message, or None if it is valid."""
    if command == "CREATE_INVOICE":
        invoice, error = resolve(data)
        return error or check_invoice(invoice)
    if command not in ("UPDATE_INVOICE", "DELETE_INVOICE", "SHOW_INVOICE"):
        return f"{command} is not an invoice command."
    invoice = storage.find(storage.load("invoices"), str(data.get("id", "")).strip().upper())
    if invoice is None:
        return f"There is no invoice {data.get('id')}."
    if command == "UPDATE_INVOICE":
        if data.get("field") not in FIELDS:
            return f"The field must be one of: {', '.join(FIELDS)}."
        return check_invoice(changed_invoice(data))
    if command == "DELETE_INVOICE" and invoice["status"] == "paid":
        return f"Invoice {invoice['id']} cannot be deleted: it is paid."
    return None


def describe_lines(lines):
    """One text for the summary: '1: 2 x Laptop x 850.00 = 1700.00; 2: ...'."""
    all_products = storage.load("products")
    return "; ".join(f"{line['line']}: {line['quantity']} x {storage.find(all_products, line['product_id'])['name']}"
                     f" x {line['unit_price']:.2f} = {line['quantity'] * line['unit_price']:.2f}" for line in lines)


def answer(command, data):
    """Answer a SHOW_INVOICE: the invoice with customer name, dates, status, lines and total."""
    invoice = storage.find(storage.load("invoices"), str(data["id"]).strip().upper())
    customer = storage.find(storage.load("customers"), invoice["customer_id"])
    return (f"{invoice['id']}: {customer['name']} | date {invoice['date']} | due {invoice['due_date']} | "
            f"{invoice['status']} | {describe_lines(invoice['lines'])} | total {invoice_total(invoice):.2f}")


def build_proposal(command, data):
    """Turn a valid command into the CRUD call the frontend makes after the user's yes, plus a summary."""
    if command == "CREATE_INVOICE":
        body, _ = resolve(data)
        body["status"] = body["status"].strip().lower()
        lines = make_lines(body["lines"])
        body["lines"] = [{"product_id": l["product_id"], "quantity": l["quantity"], "unit_price": l["unit_price"]}
                         for l in lines]
        customer = storage.find(storage.load("customers"), body["customer_id"])
        return {"method": "POST", "path": "/invoices", "body": body,
                "summary": f"Create invoice for {customer['id']} ({customer['name']}) | date {body['date']} | "
                           f"due {body['due_date']} | {body['status']} | {describe_lines(lines)} | "
                           f"total {invoice_total(body):.2f}"}
    invoice = storage.find(storage.load("invoices"), str(data["id"]).strip().upper())
    if command == "UPDATE_INVOICE":
        body = changed_invoice(data)
        field = data["field"]
        if field == "status":
            body["status"] = body["status"].lower()
        body = {key: body[key] for key in ["customer_id", "date", "due_date", "status", "lines"]}
        body["lines"] = [{"product_id": l["product_id"], "quantity": l["quantity"], "unit_price": l["unit_price"]}
                         for l in invoice["lines"]]
        return {"method": "PUT", "path": f"/invoices/{invoice['id']}", "body": body,
                "summary": f"Change {field} of {invoice['id']}: '{invoice[field]}' -> '{body[field]}'"}
    return {"method": "DELETE", "path": f"/invoices/{invoice['id']}", "body": None,
            "summary": f"Delete invoice {invoice['id']} ({invoice['customer_id']}, {invoice['date']}, "
                       f"{invoice['status']}) | total {invoice_total(invoice):.2f}"}

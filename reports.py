import calendar
from datetime import date

import customers
import invoices
import products
import storage


def paid_invoices(start, end):
    """Paid invoices whose due date is between start and end (DD/MM/YYYY, both included).
    Turnover counts only paid invoices, by due date (requirements)."""
    first, last = invoices.to_date(start), invoices.to_date(end)
    return [i for i in storage.load("invoices")
            if i["status"] == "paid" and first <= invoices.to_date(i["due_date"]) <= last]


def turnover_by_customer(start, end, product_id=None):
    """R1: turnover per customer between two dates, highest first; with product_id only that product's lines count.
    Returns [{"customer_id", "name", "turnover"}]; customers without turnover are left out."""
    totals = {}
    for invoice in paid_invoices(start, end):
        amount = sum(line["quantity"] * line["unit_price"] for line in invoice["lines"]
                     if not product_id or line["product_id"] == product_id)
        if amount:
            totals[invoice["customer_id"]] = totals.get(invoice["customer_id"], 0) + amount
    all_customers = storage.load("customers")
    return sorted(({"customer_id": cid, "name": storage.find(all_customers, cid)["name"], "turnover": round(total, 2)}
                   for cid, total in totals.items()), key=lambda row: -row["turnover"])


def turnover_by_product(start, end):
    """R2: turnover per product between two dates, highest first.
    Returns [{"product_id", "name", "quantity", "turnover"}]; products without turnover are left out."""
    totals = {}
    for invoice in paid_invoices(start, end):
        for line in invoice["lines"]:
            quantity, turnover = totals.get(line["product_id"], (0, 0))
            totals[line["product_id"]] = (quantity + line["quantity"], turnover + line["quantity"] * line["unit_price"])
    all_products = storage.load("products")
    return sorted(({"product_id": pid, "name": storage.find(all_products, pid)["name"], "quantity": quantity,
                    "turnover": round(turnover, 2)} for pid, (quantity, turnover) in totals.items()),
                  key=lambda row: -row["turnover"])


def turnover_by_month(year, customer_id=None, product_id=None):
    """R3: turnover for each month of a year (all 12 months, also those with 0), optionally for one
    customer and/or one product. Returns [{"month": 1..12, "turnover"}]."""
    totals = [0] * 12
    for invoice in paid_invoices(f"01/01/{year}", f"31/12/{year}"):
        if customer_id and invoice["customer_id"] != customer_id:
            continue
        month = invoices.to_date(invoice["due_date"]).month
        totals[month - 1] += sum(line["quantity"] * line["unit_price"] for line in invoice["lines"]
                                 if not product_id or line["product_id"] == product_id)
    return [{"month": month, "turnover": round(total, 2)} for month, total in enumerate(totals, start=1)]


def check_period(start, end):
    """Return an error message if start or end is not a valid DD/MM/YYYY date or end is before start, else None."""
    for name, value in [("start", start), ("end", end)]:
        if invoices.to_date(value) is None:
            return f"The {name} must be a valid date DD/MM/YYYY, not '{value}'."
    if invoices.to_date(end) < invoices.to_date(start):
        return "The end must not be before the start."
    return None


def period(data):
    """Turn the period of a REPORT command into (start, end) as DD/MM/YYYY texts, not yet checked.
    The bot copies what the user said: "start"/"end" dates, or a "month" (1-12) and/or a "year".
    Python fills the rest: no year means the current year, no month means the whole year."""
    if data.get("start") or data.get("end"):
        return str(data.get("start", "")), str(data.get("end", ""))
    year = str(data.get("year") or date.today().year)
    month = str(data.get("month") or "").strip()
    if not month:
        return f"01/01/{year}", f"31/12/{year}"
    first = invoices.to_date(f"01/{month}/{year}")
    if first is None:
        return f"01/{month}/{year}", f"01/{month}/{year}"  # check_period then reports the invalid date
    last_day = calendar.monthrange(first.year, first.month)[1]
    return first.strftime("%d/%m/%Y"), first.replace(day=last_day).strftime("%d/%m/%Y")


SHOW_MODULES = {"SHOW_CUSTOMER": customers, "SHOW_PRODUCT": products, "SHOW_INVOICE": invoices}


def check_command(command, data):
    """Check a command of the report bot. Return an error message, or None if it is valid."""
    if command in SHOW_MODULES:
        return SHOW_MODULES[command].check_command(command, data)
    if command == "REPORT_MONTH":
        year = str(data.get("year") or date.today().year)
        if invoices.to_date(f"01/01/{year}") is None:
            return f"The year must be a 4-digit year like 2026, not '{year}'."
        lookups = [("customer", customers.find_customers, data.get("customer")),
                   ("product", products.find_products, data.get("product"))]
    elif command in ("REPORT_CUSTOMER", "REPORT_PRODUCT"):
        error = check_period(*period(data))
        if error:
            return error
        entity = command.split("_")[1].lower()
        lookups = [(entity, customers.find_customers if entity == "customer" else products.find_products,
                    data.get("name"))]
    else:
        return f"{command} is not a report command."
    for entity, find, name in lookups:
        if not name:
            continue
        matches = find(name)
        if not matches:
            return f"There is no {entity} called {name}."
        if len(matches) > 1:
            return f"There are {len(matches)} {entity}s called {name}: " \
                   f"{', '.join(m['name'] for m in matches)}. Which one do you mean?"
    return None


def answer(command, data):
    """Answer a valid SHOW or REPORT command with Python's data or numbers as text (turnover = paid invoices, by due date)."""
    if command in SHOW_MODULES:
        return SHOW_MODULES[command].answer(command, data)
    if command == "REPORT_MONTH":
        year = str(data.get("year") or date.today().year)
        customer = customers.find_customers(data["customer"])[0] if data.get("customer") else None
        product = products.find_products(data["product"])[0] if data.get("product") else None
        rows = turnover_by_month(year, customer and customer["id"], product and product["id"])
        title = f"Turnover per month in {year}" + (f" with {customer['name']}" if customer else "") \
            + (f" for {product['name']}" if product else "")
        lines = [f"{calendar.month_name[row['month']]}: {row['turnover']:.2f}" for row in rows]
    else:
        start, end = period(data)
        is_customer = command == "REPORT_CUSTOMER"
        rows = turnover_by_customer(start, end) if is_customer else turnover_by_product(start, end)
        if data.get("name"):
            record = (customers.find_customers if is_customer else products.find_products)(data["name"])[0]
            rows = [row for row in rows if row["customer_id" if is_customer else "product_id"] == record["id"]] \
                or [{"name": record["name"], "quantity": 0, "turnover": 0}]
        title = f"Turnover per {'customer' if is_customer else 'product'} from {start} to {end}"
        lines = [f"{row['name']}: {row['turnover']:.2f}" + ("" if is_customer else f" ({row['quantity']} sold)")
                 for row in rows] or ["No paid invoices in this period."]
    total = sum(row["turnover"] for row in rows)
    return f"{title} (paid invoices, by due date):\n" + "\n".join(lines) + f"\nTotal: {total:.2f}"

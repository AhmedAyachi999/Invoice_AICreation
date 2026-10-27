from core import storage

FIELDS = ["name", "address"]


def check_customer(customer):
    """Return an error message if a field is missing or empty, else None."""
    for field in FIELDS:
        value = str(customer.get(field, "")).strip()
        if not value or value == "...":
            return f"The {field} is missing."
    return None


def create_customer(data):
    """Give the customer the next number, save it and return it."""
    customers = storage.load("customers")
    customer = {"id": storage.next_id("customers", customers), "name": data["name"].strip(),
                "address": data["address"].strip()}
    customers.append(customer)
    storage.save("customers", customers)
    return customer


def update_customer(customer_id, data):
    """Replace name and address of a customer; return it, or None if the number doesn't exist."""
    customers = storage.load("customers")
    customer = storage.find(customers, customer_id)
    if customer is None:
        return None
    customer["name"] = data["name"].strip()
    customer["address"] = data["address"].strip()
    storage.save("customers", customers)
    return customer


def delete_customer(customer_id):
    """Delete a customer; return it, None if the number doesn't exist, ValueError if it has invoices."""
    customers = storage.load("customers")
    customer = storage.find(customers, customer_id)
    if customer is None:
        return None
    used_in = [i["id"] for i in storage.load("invoices") if i["customer_id"] == customer_id]
    if used_in:
        raise ValueError(f"{customer['name']} cannot be deleted: used in invoices {', '.join(used_in)}.")
    customers.remove(customer)
    storage.save("customers", customers)
    return customer


def find_customers(name):
    """All customers whose name contains the given text (not case-sensitive).
    If one name is exactly the text, only that one (a name picked from the chooser is exact)."""
    text = str(name).strip().lower()
    found = [c for c in storage.load("customers") if text and text in c["name"].lower()]
    exact = [c for c in found if c["name"].lower() == text]
    return exact or found


def find_target(data):
    """The customers a command means: by number ("id") if the bot gave one, else by name."""
    customer_id = str(data.get("id") or "").strip().upper()
    if customer_id:
        customer = storage.find(storage.load("customers"), customer_id)
        return [customer] if customer else []
    return find_customers(data.get("name", ""))


def check_command(command, data):
    """Check a command of the customer bot. Return an error message, or None if it is valid."""
    if command == "CREATE_CUSTOMER":
        return check_customer(data)
    if command not in ("UPDATE_CUSTOMER", "DELETE_CUSTOMER", "SHOW_CUSTOMER"):
        return f"{command} is not a customer command."
    if command == "SHOW_CUSTOMER" and not str(data.get("name") or "").strip():  # list of all customers
        return None
    matches = find_target(data)
    if not matches and str(data.get("id") or "").strip():
        return f"There is no customer {data['id']}. Which customer do you mean?"  # "which customer": the chooser opens
    if not matches:
        return f"There is no customer called {data.get('name')}."
    if command == "SHOW_CUSTOMER":
        return None
    if len(matches) > 1:
        return f"There are {len(matches)} customers called {data.get('name')}: " \
               f"{', '.join(c['name'] for c in matches)}. Which one do you mean?"
    customer = matches[0]
    if command == "UPDATE_CUSTOMER":
        return check_customer({**customer, data.get("field"): data.get("value")}) if data.get("field") in FIELDS \
            else f"The field must be one of: {', '.join(FIELDS)}."
    used_in = [i["id"] for i in storage.load("invoices") if i["customer_id"] == customer["id"]]
    if used_in:
        return f"{customer['name']} cannot be deleted: used in invoices {', '.join(used_in)}."
    return None


LIST_LIMIT = 10  # at most this many customers in one chat answer


def answer(command, data):
    """Answer a SHOW_CUSTOMER: one line per customer whose name matches, or all customers (at most LIST_LIMIT)."""
    name = str(data.get("name") or "").strip()
    found = find_customers(name) if name else storage.load("customers")
    lines = [f"{c['id']}: {c['name']} | {c['address']}" for c in found[:LIST_LIMIT]]
    if len(found) > LIST_LIMIT:
        lines.append(f"... and {len(found) - LIST_LIMIT} more. Please write a name to narrow it down.")
    return "\n".join(lines)


def build_proposal(command, data):
    """Turn a valid command into the CRUD call the frontend makes after the user's yes, plus a summary."""
    if command == "CREATE_CUSTOMER":
        body = {"name": data["name"].strip(), "address": data["address"].strip()}
        return {"method": "POST", "path": "/customers", "body": body,
                "summary": f"Create customer: {body['name']} | {body['address']}"}
    customer = find_target(data)[0]
    if command == "UPDATE_CUSTOMER":
        body = {"name": customer["name"], "address": customer["address"], data["field"]: data["value"].strip()}
        return {"method": "PUT", "path": f"/customers/{customer['id']}", "body": body,
                "summary": f"Change {data['field']} of {customer['id']} ({customer['name']}): "
                           f"'{customer[data['field']]}' -> '{body[data['field']]}'"}
    return {"method": "DELETE", "path": f"/customers/{customer['id']}", "body": None,
            "summary": f"Delete customer {customer['id']}: {customer['name']} | {customer['address']}"}

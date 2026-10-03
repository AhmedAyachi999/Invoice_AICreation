import json

import storage

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


def data_block():
    """The <CUSTOMER DATA> block for the customer bot: all customers with number, name and address."""
    return f"<CUSTOMER DATA>\n{json.dumps(storage.load('customers'), ensure_ascii=False)}\n</CUSTOMER DATA>"


def check_command(name, data):
    """Check a command of the customer bot. Return an error message for the bot, or None if it is valid."""
    if name == "CREATE_CUSTOMER":
        return check_customer(data)
    if name not in ("UPDATE_CUSTOMER", "DELETE_CUSTOMER"):
        return f"{name} is not a customer command."
    customer = storage.find(storage.load("customers"), data.get("id"))
    if customer is None:
        return f"There is no customer with id {data.get('id')}."
    if name == "UPDATE_CUSTOMER":
        return check_customer({**customer, data.get("field"): data.get("value")}) if data.get("field") in FIELDS \
            else f"The field must be one of: {', '.join(FIELDS)}."
    used_in = [i["id"] for i in storage.load("invoices") if i["customer_id"] == customer["id"]]
    if used_in:
        return f"{customer['name']} cannot be deleted: used in invoices {', '.join(used_in)}."
    return None


def build_proposal(name, data):
    """Turn a valid command into the CRUD call the frontend makes after the user's yes, plus a summary."""
    if name == "CREATE_CUSTOMER":
        body = {"name": data["name"].strip(), "address": data["address"].strip()}
        return {"method": "POST", "path": "/customers", "body": body,
                "summary": f"Create customer: {body['name']} | {body['address']}"}
    customer = storage.find(storage.load("customers"), data["id"])
    if name == "UPDATE_CUSTOMER":
        body = {"name": customer["name"], "address": customer["address"], data["field"]: data["value"].strip()}
        return {"method": "PUT", "path": f"/customers/{customer['id']}", "body": body,
                "summary": f"Change {data['field']} of {customer['id']} ({customer['name']}): "
                           f"'{customer[data['field']]}' -> '{body[data['field']]}'"}
    return {"method": "DELETE", "path": f"/customers/{customer['id']}", "body": None,
            "summary": f"Delete customer {customer['id']}: {customer['name']} | {customer['address']}"}

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

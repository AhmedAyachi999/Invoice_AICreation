from core import storage

FIELDS = ["name", "sell_price"]


def check_product(product):
    """Return an error message if the name or sell_price is missing or the sell_price is not a number >= 0, else None."""
    name = str(product.get("name", "")).strip()
    if not name or name == "...":
        return "The name is missing."
    value = product.get("sell_price")
    value = "" if value is None else str(value).strip()
    if not value or value == "...":
        return "The sell_price is missing."
    try:
        price = float(value.replace(",", "."))
    except ValueError:
        return f"The sell_price must be a number, not '{value}'."
    if price < 0:
        return "The sell_price must not be negative."
    return None


def to_price(value):
    """Turn a price like 12.5, "12.5" or "12,5" into a float; None or empty gives None."""
    if value is None or str(value).strip() == "":
        return None
    return float(str(value).strip().replace(",", "."))


def create_product(data):
    """Give the product the next code, save it with its sell price as a number and return it."""
    products = storage.load("products")
    product = {"id": storage.next_id("products", products), "name": data["name"].strip(),
               "sell_price": to_price(data["sell_price"])}
    products.append(product)
    storage.save("products", products)
    return product


def update_product(product_id, data):
    """Replace name and sell price of a product; return it, or None if the code doesn't exist. Invoices are not touched."""
    products = storage.load("products")
    product = storage.find(products, product_id)
    if product is None:
        return None
    product["name"] = data["name"].strip()
    product["sell_price"] = to_price(data["sell_price"])
    storage.save("products", products)
    return product


def delete_product(product_id):
    """Delete a product; return it, None if the code doesn't exist, ValueError if an invoice line uses it."""
    products = storage.load("products")
    product = storage.find(products, product_id)
    if product is None:
        return None
    used_in = [i["id"] for i in storage.load("invoices")
               if any(line["product_id"] == product_id for line in i["lines"])]
    if used_in:
        raise ValueError(f"{product['name']} cannot be deleted: used in invoices {', '.join(used_in)}.")
    products.remove(product)
    storage.save("products", products)
    return product


def find_products(name):
    """All products whose name contains the given text (not case-sensitive).
    If one name is exactly the text, only that one (a name picked from the chooser is exact)."""
    text = str(name).strip().lower()
    found = [p for p in storage.load("products") if text and text in p["name"].lower()]
    exact = [p for p in found if p["name"].lower() == text]
    return exact or found


def check_command(command, data):
    """Check a command of the product bot. Return an error message, or None if it is valid."""
    if command == "CREATE_PRODUCT":
        return check_product(data)
    if command not in ("UPDATE_PRODUCT", "DELETE_PRODUCT", "SHOW_PRODUCT"):
        return f"{command} is not a product command."
    matches = find_products(data.get("name", ""))
    if not matches:
        return f"There is no product called {data.get('name')}."
    if command == "SHOW_PRODUCT":
        return None
    if len(matches) > 1:
        return f"There are {len(matches)} products called {data.get('name')}: " \
               f"{', '.join(p['name'] for p in matches)}. Which one do you mean?"
    product = matches[0]
    if command == "UPDATE_PRODUCT":
        return check_product({**product, data.get("field"): data.get("value")}) if data.get("field") in FIELDS \
            else f"The field must be one of: {', '.join(FIELDS)}."
    used_in = [i["id"] for i in storage.load("invoices")
               if any(line["product_id"] == product["id"] for line in i["lines"])]
    if used_in:
        return f"{product['name']} cannot be deleted: used in invoices {', '.join(used_in)}."
    return None


def answer(command, data):
    """Answer a SHOW_PRODUCT: one line per product whose name matches."""
    return "\n".join(f"{p['id']}: {p['name']} | sell price {p['sell_price']}" for p in find_products(data["name"]))


def build_proposal(command, data):
    """Turn a valid command into the CRUD call the frontend makes after the user's yes, plus a summary."""
    if command == "CREATE_PRODUCT":
        body = {"name": data["name"].strip(), "sell_price": to_price(data["sell_price"])}
        return {"method": "POST", "path": "/products", "body": body,
                "summary": f"Create product: {body['name']} | sell price {body['sell_price']}"}
    product = find_products(data["name"])[0]
    if command == "UPDATE_PRODUCT":
        field = data["field"]
        value = str(data["value"]).strip() if field == "name" else to_price(data["value"])
        body = {"name": product["name"], "sell_price": product["sell_price"], field: value}
        return {"method": "PUT", "path": f"/products/{product['id']}", "body": body,
                "summary": f"Change {field} of {product['id']} ({product['name']}): "
                           f"'{product[field]}' -> '{body[field]}'"}
    return {"method": "DELETE", "path": f"/products/{product['id']}", "body": None,
            "summary": f"Delete product {product['id']}: {product['name']} | sell price {product['sell_price']}"}

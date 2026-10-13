"""Fill the empty database with test data: similar names, similar products, paid and unpaid invoices.
Usage: python tests/seed_data.py (only on an empty database)"""
import customers
import invoices
import products
import storage

CUSTOMERS = [
    ("Felix Hartmann", "Seeweg 4, 24103 Kiel"), ("Greta Hartman", "Lindenallee 12, 20259 Hamburg"),
    ("Jonas Müller", "Bahnhofstr. 3, 80335 München"), ("Lena Müller", "Gartenweg 7, 50667 Köln"),
    ("Paul Müller-Lang", "Marktplatz 1, 70173 Stuttgart"), ("Anna Schmidt", "Rosenstr. 9, 10115 Berlin"),
    ("Annabel Schmitt", "Hafenstr. 21, 28195 Bremen"), ("Karl Becker", "Ringstr. 5, 01067 Dresden"),
    ("Karla Bäcker", "Schulweg 2, 04109 Leipzig"), ("Omar Haddad", "Mühlenweg 8, 30159 Hannover"),
    ("Sofia Rossi", "Kirchplatz 6, 90402 Nürnberg"), ("Tim Wagner", "Feldstr. 14, 44135 Dortmund"),
]
PRODUCTS = [
    ("Desk Lamp", 29.9, 12.5), ("Desk Lamp Pro", 49.9, 21), ("Office Chair", 189, 95),
    ("Office Chair Comfort", 249, 130), ("USB Cable 1m", 6.5, 1.2), ("USB Cable 2m", 8.5, 1.6),
    ("Laptop Stand", 39, None), ("Monitor 24", 159, 110), ("Monitor 27", 229, 160), ("Notebook A5", 3.2, 0.8),
]
INVOICES = [  # customer, date, due date, status, [(product, quantity)]
    ("Felix Hartmann", "02/09/2026", "02/10/2026", "paid", [("Desk Lamp", 2), ("USB Cable 1m", 5)]),
    ("Felix Hartmann", "15/09/2026", "15/10/2026", "unpaid", [("Office Chair", 1)]),
    ("Greta Hartman", "20/09/2026", "20/10/2026", "unpaid", [("Monitor 24", 2), ("USB Cable 2m", 2)]),
    ("Jonas Müller", "01/10/2026", "31/10/2026", "unpaid", [("Laptop Stand", 3)]),
    ("Lena Müller", "03/10/2026", "02/11/2026", "paid", [("Notebook A5", 20), ("Desk Lamp Pro", 1)]),
    ("Anna Schmidt", "05/10/2026", "04/11/2026", "unpaid", [("Office Chair Comfort", 2), ("Monitor 27", 2)]),
    ("Karl Becker", "06/10/2026", "05/11/2026", "paid", [("USB Cable 1m", 10)]),
    ("Omar Haddad", "07/10/2026", "06/11/2026", "unpaid", [("Desk Lamp", 1), ("Monitor 27", 1)]),
]

if storage.load("customers") or storage.load("products") or storage.load("invoices"):
    raise SystemExit("The database is not empty; nothing was added.")
customer_ids = {name: customers.create_customer({"name": name, "address": address})["id"]
                for name, address in CUSTOMERS}
product_ids = {name: products.create_product({"name": name, "sell_price": sell, "buy_price": buy})["id"]
               for name, sell, buy in PRODUCTS}
for customer, date, due, status, lines in INVOICES:
    invoices.create_invoice({"customer_id": customer_ids[customer], "date": date, "due_date": due, "status": status,
                             "lines": [{"product_id": product_ids[p], "quantity": q} for p, q in lines]})
print(f"Added {len(CUSTOMERS)} customers, {len(PRODUCTS)} products, {len(INVOICES)} invoices.")

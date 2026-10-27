import json
import os
import sqlite3
from pathlib import Path

DB_PATH = Path(os.environ.get("INVOICE_DB_PATH", Path(__file__).parent.parent.parent / "data" / "invoices.db"))
SEED = Path(__file__).parent.parent.parent / "seed" / "demo_data.json"  # example data for a reproducible demo


def connect():
    """Open the SQLite database file (INVOICE_DB_PATH, default data/invoices.db; created if it doesn't exist yet)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    """Create the four tables if they don't exist yet."""
    with connect() as connection:
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, address TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, name TEXT NOT NULL, sell_price REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS invoices (
                id TEXT PRIMARY KEY, customer_id TEXT NOT NULL REFERENCES customers(id),
                date TEXT NOT NULL, due_date TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS invoice_lines (
                invoice_id TEXT NOT NULL REFERENCES invoices(id), line INTEGER NOT NULL,
                product_id TEXT NOT NULL REFERENCES products(id), quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL, PRIMARY KEY (invoice_id, line));
        """)


def load(entity):
    """Return the records of an entity ("customers", "products", "invoices") as a list of dicts."""
    create_tables()
    with connect() as connection:
        records = [dict(row) for row in connection.execute(f"SELECT * FROM {entity} ORDER BY id")]
        if entity == "invoices":
            for invoice in records:
                lines = connection.execute(
                    "SELECT line, product_id, quantity, unit_price FROM invoice_lines "
                    "WHERE invoice_id = ? ORDER BY line", (invoice["id"],))
                invoice["lines"] = [dict(line) for line in lines]
    return records


def save(entity, records):
    """Replace all records of an entity in the database with the given list."""
    create_tables()
    with connect() as connection:
        connection.execute(f"DELETE FROM {entity}")
        if entity == "invoices":
            connection.execute("DELETE FROM invoice_lines")
        for record in records:
            fields = {key: value for key, value in record.items() if key != "lines"}
            connection.execute(f"INSERT INTO {entity} ({', '.join(fields)}) VALUES ({', '.join('?' * len(fields))})",
                               list(fields.values()))
            for line in record.get("lines", []):
                connection.execute(
                    "INSERT INTO invoice_lines (invoice_id, line, product_id, quantity, unit_price) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (record["id"], line["line"], line["product_id"], line["quantity"], line["unit_price"]))


def seed():
    """On the first start (no database file yet), fill the new database with the example data."""
    if DB_PATH.exists():
        return
    data = json.loads(SEED.read_text(encoding="utf-8"))
    for entity in ("customers", "products", "invoices"):
        save(entity, data[entity])


PREFIXES = {"customers": "CUS", "products": "PRD", "invoices": "INV"}


def next_id(entity, records):
    """Next number: one above the highest existing one, e.g. CUS-003 after CUS-002."""
    numbers = [int(r["id"].split("-")[1]) for r in records]
    return f"{PREFIXES[entity]}-{max(numbers, default=0) + 1:03d}"


def find(records, record_id):
    """Return the record with this number, or None if it doesn't exist."""
    return next((r for r in records if r["id"] == record_id), None)

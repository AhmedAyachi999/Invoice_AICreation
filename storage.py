import json
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"


def load(entity):
    """Return the records of an entity ("customers", "products", "invoices"), or [] if there are none yet."""
    path = DATA_DIR / f"{entity}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def save(entity, records):
    """Write the records of an entity to its JSON file."""
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / f"{entity}.json"
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")


PREFIXES = {"customers": "CUS", "products": "PRD", "invoices": "INV"}


def next_id(entity, records):
    """Next number: one above the highest existing one, e.g. CUS-003 after CUS-002."""
    numbers = [int(r["id"].split("-")[1]) for r in records]
    return f"{PREFIXES[entity]}-{max(numbers, default=0) + 1:03d}"


def find(records, record_id):
    """Return the record with this number, or None if it doesn't exist."""
    return next((r for r in records if r["id"] == record_id), None)

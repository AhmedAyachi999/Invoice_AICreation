"""Unit tests for the Python guards, without a bot: fast, same result every time.
They run on an empty test database filled by seed_data.py, never on data/invoices.db.
Usage: python tests/guard_tests.py"""
import pathlib
import runpy
import tempfile

from core import storage

storage.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "guard.db"  # a new, empty test database
storage.create_tables()
runpy.run_path(str(pathlib.Path(__file__).with_name("seed_data.py")))  # fixed data: 12 customers, 10 products, 8 invoices

from chat import assistant, bot, router
from entities import invoices

USER = lambda text: [{"role": "user", "content": text}]  # a conversation with one user message

CASES = [  # (id, what is tested, result, expected)
    ("G1", "negative price is caught", bool(router.NEGATIVE_PRICE.search("sell price -5")), True),
    ("G2", "negative price with a space", bool(router.NEGATIVE_PRICE.search("sell price - 5")), True),
    ("G3", "hyphen in a product name is no price", bool(router.NEGATIVE_PRICE.search("new product USB-3 Cable, sell price 5")), False),
    ("G4", "name the user never wrote", bot.invented_target("DELETE_PRODUCT", {"name": "Kettle Varo"}, USER("delete")), "Kettle Varo"),
    ("G5", "name the user wrote", bot.invented_target("DELETE_PRODUCT", {"name": "Kettle Varo"}, USER("remove Kettle Varo")), None),
    ("G6", "shorter name inside the user's name", bot.invented_target("DELETE_PRODUCT", {"name": "Lamp"}, USER("delete the Desk Lamp")), "Lamp"),
    ("G7", "CREATE is not checked", bot.invented_target("CREATE_PRODUCT", {"name": "Tea Cup"}, USER("add a product")), None),
    ("G8", "paid invoice cannot be deleted", invoices.check_command("DELETE_INVOICE", {"id": "INV-001"}),
     "Invoice INV-001 cannot be deleted: it is paid."),
    ("G9", "unpaid invoice can be deleted", invoices.check_command("DELETE_INVOICE", {"id": "INV-002"}), None),
    ("G10", "unknown invoice", invoices.check_command("DELETE_INVOICE", {"id": "INV-640"}), "There is no invoice INV-640."),
    # form_turnover: one case per form message of static/app.js (the contract between the page and Python)
    ("G11", "form: per customer, all", assistant.form_turnover(
        "turnover per customer from 01/09/2026 to 31/10/2026, all customers"),
     "from 01/09/2026 to 31/10/2026: Felix Hartmann 92.30, total 92.30."),
    ("G12", "form: per customer, one product", assistant.form_turnover(
        "turnover per customer from 01/09/2026 to 31/10/2026, all customers, product: USB Cable 1m (PRD-005)"),
     "from 01/09/2026 to 31/10/2026, product USB Cable 1m: Felix Hartmann 32.50, total 32.50."),
    ("G13", "form: per product, one product", assistant.form_turnover(
        "turnover per product from 01/09/2026 to 31/10/2026, product: Desk Lamp"),
     "from 01/09/2026 to 31/10/2026, product Desk Lamp: Desk Lamp 59.80, total 59.80."),
    ("G14", "form: per product, one customer", assistant.form_turnover(
        "turnover per product from 01/09/2026 to 30/11/2026, all products, customer: Karl Becker (CUS-008)"),
     "from 01/09/2026 to 30/11/2026, customer Karl Becker: USB Cable 1m 65.00, total 65.00."),
    ("G15", "form: monthly, customer + product", assistant.form_turnover(
        "monthly turnover for 2026, customer: Lena Müller (CUS-004), product: Notebook A5 (PRD-010)").endswith(
        "October 0.00, November 64.00, December 0.00, total 64.00."), True),
    ("G16", "form: end before start", assistant.form_turnover(
        "turnover per customer from 31/10/2026 to 01/09/2026, all customers"), "The end must not be before the start."),
    ("G17", "typed text is no form message", assistant.form_turnover("turnover by customer"), None),
]

wrong = 0
for case_id, what, result, expected in CASES:
    ok = result == expected
    wrong += not ok
    print(f"{case_id}\t{'OK   ' if ok else 'WRONG'}\t{what}\n\t\tgot: {result!r}  expected: {expected!r}")
print(f"\n{len(CASES) - wrong}/{len(CASES)} OK")

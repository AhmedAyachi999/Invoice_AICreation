# Bot tests

Tests for the Ollama bots. They need Ollama running and the bots built from `modelfiles/` (see the main README).
Most of them call the bot directly (`bot.chat`), so they measure the bot alone; `target_tests.py` goes through
`bot.converse`, i.e. with the Python checks.

Run from the project root (PowerShell):

```
$env:PYTHONPATH = (Resolve-Path app).Path; $env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe tests\bot_only.py inv-customer-bot G      # customers: G1-G15 (development set)
.\.venv\Scripts\python.exe tests\bot_only.py inv-customer-bot N      # customers: N1-N15 (hold-out, never tuned on)
.\.venv\Scripts\python.exe tests\fresh_tests.py inv-customer-bot     # customers: H1-H20 (fresh names and wording)
.\.venv\Scripts\python.exe tests\product_tests.py                    # products: P1-P20
.\.venv\Scripts\python.exe tests\invoice_tests.py                    # invoices: V1-V20
.\.venv\Scripts\python.exe tests\danger_tests.py                     # 30 dangerous cases (invented records/values)
.\.venv\Scripts\python.exe tests\target_tests.py                     # 5 cases without a named record, through converse
.\.venv\Scripts\python.exe tests\seed_data.py                        # fills an EMPTY database with test data
```

| File | Content |
|---|---|
| `general_tests.py` | G1-G15 and the strict answer check `is_correct` (also used by the other customer tests) |
| `new_scenarios.py` | N1-N15 |
| `bot_only.py`, `fresh_tests.py` | Run the customer sets above against a bot |
| `product_tests.py`, `invoice_tests.py` | Product and invoice sets |
| `danger_tests.py` | Danger set: a case passes if there is no command, or every value comes from the message |
| `target_tests.py` | Messages that name no record; Python must ask instead of proposing |
| `seed_data.py` | Test data (similar names, paid and unpaid invoices) for an empty database |

`general_tests.py` and `new_scenarios.py` also contain the old judge loop from episode 3. The judge bot was dropped,
so run these sets through `bot_only.py`.

Results vary by about +-1 between runs, even at temperature 0, so important measurements are run twice.

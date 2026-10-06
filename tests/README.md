# Bot tests

Tests for the customer bot (`inv-customer-bot`) and the judge (`inv-judge-bot`). They need Ollama running and the
bots built from the Modelfiles in the project root.

Run from the project root (PowerShell):

```
$env:PYTHONPATH = (Get-Location).Path; $env:PYTHONIOENCODING = "utf-8"
.\.venv\Scripts\python.exe tests\fresh_tests.py inv-customer-bot     # 20 fresh scenarios H1-H20, no judge
.\.venv\Scripts\python.exe tests\bot_only.py inv-customer-bot G      # general tests G1-G15, no judge
.\.venv\Scripts\python.exe tests\bot_only.py inv-customer-bot N      # hold-out scenarios N1-N15, no judge
.\.venv\Scripts\python.exe tests\general_tests.py                    # G1-G15 with the judge loop
.\.venv\Scripts\python.exe tests\coach_loop.py                       # N1-N15 with the judge loop
```

| File | Content |
|---|---|
| `general_tests.py` | G1-G15 (development set used for tuning) and the strict answer check |
| `new_scenarios.py` | N1-N15 (hold-out set, never used for tuning) |
| `fresh_tests.py` | H1-H20 (fresh scenarios, new names and wording) |
| `results/` | Results of the tuning agent (`dev_*`, `dev2_*`, `holdout*`) from episode 4 |

The checks are automatic and partly lenient (addresses are checked by a substring). Results vary by about +-1
between runs, even at temperature 0.

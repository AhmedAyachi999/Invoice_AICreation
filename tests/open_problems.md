# Open problems – handoff

Last update: 14/10/2026 · Last commit: Episode 9 (RAG help)

| Before you start | |
|---|---|
| Server | • uvicorn **without** `--reload` → restart after every Python change<br>• frontend cache: `app.js?v=20` in `index.html` |
| Database | • tests on a **copy** of `data/invoices.db`, never the real one<br>• INV-002 was deleted by hand |
| Turnover | • only **paid** invoices, counted by **due date** |
| Next tests | • **`tests/test_plan.md`**: intention, copying from examples, no change without "Yes" (planned, not written) |

## A. Still open

| # | Problem | Details | Possible fix |
|---|---|---|---|
| 1 | "is INV-011 paid?" → "unpaid" | • INV-011 **is** paid<br>• the bot got the 4 paid invoices and still said no | – |
| 2 | 3413 identical tool calls | • seen once: "address of Mara Quist?"<br>• `MAX_ROUNDS` limits rounds, not calls | • skip identical calls<br>• cap calls per round |
| 3 | Paid invoice deletable in 2 steps | • set to unpaid, then delete | • decide if OK |
| 4 | Tool descriptions outdated | • `ask_*`: "when the user did not write both dates" (now: always the form)<br>• `get_turnover_by_product` has no `customer_id` | • update `TOOLS` |
| 5 | "how many invoices are paid?" | • gives a list instead of the number | – |
| 6 | Invoice bot asks again | • for info already given | • mitigated by forms |
| 7 | Product rename after chooser | • unreliable → edit form only covers prices | – |
| 8 | Assistant format | • sometimes only "Analysis:", no "Answer:" | – |
| 9 | `NEGATIVE_PRICE` regex | • matches "USB-3 Cable" | • guard unit test |
| 10 | `period_from_user` | • unused since "always the form" | • remove |
| 11 | Router: "add a customer named Lena Berg" | • → `question` (0/5) | – |
| 12 | Router: "INV-004 is paid" | • → `question` (0/5), it is a change | – |
| 13 | Router: "remove Tim Wagner" | • → `none` (0/5): name not seen as a customer | – |
| 14 | Product bot copies "Kettle Varo" | • "change the price" → "What is the new sell price of Kettle Varo?" (5/5), no form | – |
| 15 | Customer bot copies "Tom Fischer" | • "update the address" → "What is the new address of Tom Fischer?" (5/5); `invented_target` catches the command | – |
| 16 | Assistant invents "Copper Kettle" | • "how much does the kettle cost?" → "The Copper Kettle costs 49.8." (5/5) – product does not exist | – |
| 17 | Help (RAG) invents / too strict | • "export to Excel?" → invented "Export" button<br>• "remove a bill" → "I don't know" | • guard: quoted names must be in the sections<br>• guide: "no export" line |
| 18 | Test cases wrong (not the bot) | • `confirm-product-delete`, `confirm-pressure-product`, `copy-delete` use "USB Cable 1m" – it is on invoices, Python refuses correctly | • use a product without invoices |
| – | Skipped (user decision) | • "how many invoices are open?" → 11<br>• "delete all unpaid invoices"<br>• turnover as free text with dates | – |

## B. Solved – don't redo

| Area | What |
|---|---|
| Router | • thinks step by step: Intention / To do that / So → `Route:`<br>• `route()` reads only after "route:" |
| Assistant | • `show_invoices`: Python writes the list<br>• `get_invoices(status)` + count<br>• synonyms open/pending = unpaid, settled = paid<br>• Example 8 removed (fake ids leaked)<br>• "show me" in front of turnover questions<br>• turnover question in free text → always the form |
| Turnover | • `form_turnover`: Python answers all 3 forms, no bot<br>• nothing selected = all<br>• `turnover_by_product(customer_id)` |
| Checks | • paid invoice not deletable (check + HTTP 400)<br>• negative price → form again<br>• name chooser: exact match first |
| Help (RAG) | • `app/guide.py` + `docs/user_guide.md` (21 sections), Help button → `/help`; router not changed (user decision) |
| Forms | • invoice chooser (sends bare id)<br>• Paid/Unpaid buttons<br>• new customer / new product<br>• price edit<br>• customer field in product turnover |

## C. Tested (13/10/2026)

| Test | Result |
|---|---|
| Turnover forms T1–T11 (per customer, per product, monthly) | 11/11 ✅ |
| Typed question → right form (12 wordings + 11 synonyms) | 23/23 ✅ |
| CRUD scenarios with forms (earlier run, 14) | 14/14 ✅ |
| Repeated tests through the forms, 5× (14/10, `tests/results/2026-10-14_repeat_tests.md`) | • no DB change without "Yes": 60/60 ✅<br>• intention: 20/23 cases 5/5 (11–13 above)<br>• copying: 10/13 clean (14–16 above) |
| `tests/guard_tests.py` (no bot) | 15/17 – G3, G6 = known bugs |

• Tests = scripts in the session scratchpad, not in the repo<br>
• Rule: show bot output verbatim first

## D. Ideas from the workshop zips

| Project | Their idea | Ours today | To do? |
|---|---|---|---|
| **shopkeeper** | • 2 agents: parser + NPC | • router + bots | ✅ same |
| | • JSON Schema output (Ollama `format`) | • text commands, Python parses | ✗ dropped (user decision 14/10) |
| | • Python allows the action | • `check_command` + user's "Yes" | ✅ same |
| | • fixed guard on every answer | • guards on input/commands, not on answer text | – |
| | • unit tests for the guard | • `tests/guard_tests.py` (14/10): 15/17, G3 + G6 = known bugs | ✅ started |
| **instectai** | • labelled prompts (category, difficulty) | • `tests/cases/*.jsonl` with category, expected, difficulty | ✅ done |
| | • 20 runs per prompt | • 5 runs through the forms (`tests/test_plan.md`), no threshold | 🔄 running |
| | • 2 scorers (safe + right behaviour) | • repeat tests: 2 checks (e.g. db unchanged + right reaction); answer **content** not checked | ⚠️ partly |
| | • rate + 95% bound | • "9/12" | – |
| | • the check can be wrong | • INV-011 counted PASS | – |
| | • logs of every run | • `tests/results/<date>_repeat_tests.md` + raw log | ✅ done |
| **client-sdk** | • llm + loop + tools + history | • same in `assistant.converse` | ✅ same |
| | • no history management (todo) | • none: bot copied 3271.20 from history | • later |
| | • date tool (local clock) | • none → "year": "this year" | • maybe |
| | • errors back to the model | • assistant yes, entity bots → user | – |
| **monolith** | • contracts written down | • form messages `app.js` ↔ `form_turnover` are a contract | ✅ G11–G16 in `guard_tests.py` |
| **plan-to-pr** | • agent team workflow | – | ✗ not useful |
| **Skills** | • reusable steps (`SKILL.md`) | • none in the project | • maybe `/run-scenarios` |

### Weak spots of `invented_target` (for guard tests)
• checks only `name`/`id`, not new values<br>
• substring: user "Desk Lamp", bot "Lamp" → not caught<br>
• doesn't run for assistant tool calls (`CUS-061` got through)

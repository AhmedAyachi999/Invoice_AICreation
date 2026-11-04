# AI Invoice Assistant

**The service manages customers, products and invoices through a chat in plain English and calculates the
turnover** – with a local language model that understands the user and Python that checks, calculates and saves.

It runs entirely on one computer: a FastAPI service with its own SQLite database and website, and a local model
server (Ollama, llama3.2:3b). No data leaves the computer.

Documents for the submission are in [`docs/submission/`](docs/submission):
[problem and core scenarios](docs/submission/3_problem_and_scenarios.md) ·
[architecture overview](docs/submission/4_architecture_overview.pdf) ·
[API (OpenAPI)](docs/submission/5_api_openapi.json) ·
[responsible design](docs/submission/7_responsible_design.md)

## 1. Problem and responsibility

A small company has to manage customers, products and invoices and needs its turnover per customer, per product
and per month. By hand in spreadsheets this is slow and error-prone (wrong totals, duplicate numbers, reports added
up manually).

The service is responsible for exactly this: storing customers, products and invoices, checking every change
against the business rules, and calculating the turnover. The user works in plain English; the AI understands the
request, Python decides. **The chat never saves** – it returns a checked proposal, and only the user's "Yes" saves it.

## 2. Core scenario

Create an invoice through the chat (all four core scenarios with the real answers:
[3_problem_and_scenarios.md](docs/submission/3_problem_and_scenarios.md)):

1. The user types *"new invoice for Karl Becker"*. The router bot sends it to the invoice bot, which asks for the
   dates; the website opens a date picker.
2. The bot asks for the products and the customer and whether the invoice is paid; each answer comes from a form
   or a list of existing records.
3. Python looks up the names in the database and replaces them by the record numbers (Karl Becker → CUS-008,
   Desk Lamp → PRD-001), takes the product's price and shows the summary
   *"Create invoice for CUS-008 (Karl Becker) | … | 1: 2 x Desk Lamp x 29.90 = 59.80 | total 59.80"* with Yes / No.
4. On Yes the website calls `POST /invoices`; Python checks everything again and saves it as INV-0xx.

## 3. Architecture and data flow

```
browser (static/) ──HTTP/JSON──▶ REST API (app/api.py) ──┬─▶ chat services (app/chat) ──▶ model server (Ollama)
                                                          │      router · change bots · assistant · Help
                                                          ▼             │ checked commands, proposals
                                          business logic (app/entities, app/core/reports) – no AI
                                                          ▼
                                          storage.py ──▶ SQLite (invoices.db)
```

- **Chat:** the router bot decides whether a message is a change (→ customer, product or invoice bot) or a
  question (→ the assistant, which reads the data with tools and can also propose a change). A change bot answers with a command like
  `DELETE_CUSTOMER {"name": "Tim Wagner"}`; Python checks it (exists? used in invoices?) and returns a proposal.
- **Saving:** the website sends the proposal to the CRUD endpoint after the user's Yes; the endpoint checks again.
- **Reports and CRUD** never use the AI.

Diagram: [4_architecture_overview.pdf](docs/submission/4_architecture_overview.pdf). Design decisions:
`docs/submission/architecture.pdf`.

```
app/
  api.py            REST API: CRUD, reports, chat endpoints, /help, /health; serves the website
  chat/             everything with a language model
    bot.py            talks to the model server (OpenAI-compatible), runs the change bots with Python's guards
    router.py         the single chat: sends each message to a change bot or to the assistant, picks the forms
    assistant.py      questions: the bot with tools (read data, turnover forms, proposals for changes)
    guide.py          Help button: answers from docs/user_guide.md (RAG with local embeddings)
  entities/         customers.py, products.py, invoices.py: checks, lookup by name, create/change/delete, proposals
  core/             no AI: storage.py (SQLite, numbers), reports.py (turnover R1–R3)
modelfiles/       the bots' instructions (router, customer, product, invoice)
static/           the website
seed/             example data for a new database (invented, no real persons)
tests/            automated tests and results (tests/results/)
docs/             user guide, open problems, submission documents (incl. requirements, design decisions, model choice)
data/             the database invoices.db (created on first start, not in git)
```

## 4. Persistence

- **SQLite**, one file: `data/invoices.db` (in Docker: the volume `/service/data`). Tables `customers`, `products`,
  `invoices`, `invoice_lines`.
- On the **first start** (no file yet) the database is filled with the example data from `seed/demo_data.json`.
- Only `app/core/storage.py` touches the database; every value is passed as an SQL parameter.
- Numbers (CUS-001, PRD-001, INV-001) are given by Python; an invoice line keeps the price of the day.
- Chat conversations are kept in memory only (lost on restart).

## 5. User interface

The website at `http://127.0.0.1:8000`:

- **one chat** on the left: plain English; the bots open **forms and pickers** when they need data (dates, customer,
  product lines, turnover period); every change ends with a summary and **Yes / No**
- **tables** on the right: Customers, Products, Invoices
- **Help** button: questions about using the program, answered from the user guide
- every message from a language model carries an **"AI" badge**; the router's reasoning and the data Python read are
  shown with the answer

## 6. API and integration

Interactive documentation: `http://127.0.0.1:8000/docs` · OpenAPI file:
[5_api_openapi.json](docs/submission/5_api_openapi.json).

| Endpoint | Purpose | AI |
|---|---|---|
| `POST /chat` | the single chat used by the website (router → change bot or assistant); returns a reply or a proposal | yes |
| `POST /customers/chat`, `/products/chat`, `/invoices/chat`, `/assistant/chat` | one bot directly | yes |
| `POST /help` | Help: answer from the user guide | yes |
| `GET/POST/PUT/DELETE /customers`, `/products`, `/invoices` | CRUD; checks again before saving | no |
| `GET /reports/customers?start&end`, `/reports/products?start&end`, `/reports/months?year&customer_id&product_id` | turnover R1–R3 (paid invoices, by due date) | no |
| `GET /health` | `ok`, or `degraded` when the model server is unreachable | no |

Errors: `{"detail": "…"}` with 400 (data not valid), 404 (number not found), 422 (request malformed), 503 (model
server or database not available). Dates are DD/MM/YYYY.

**Integration:** other programs use only this REST API (e.g. `curl http://127.0.0.1:8000/customers`); nobody
else accesses the database. The service needs no other service except the model server; without it, everything
but the chat keeps working.

## 7. Local model and inference server

| | |
|---|---|
| Inference server | **Ollama 0.40.11**, OpenAI-compatible API at `http://localhost:11434/v1` |
| Chat model | **llama3.2:3b** (2.0 GB), temperature 0 – used as four bots built from `modelfiles/` (`inv-router-bot`, `inv-customer-bot`, `inv-product-bot`, `inv-invoice-bot`) and directly for the assistant and Help |
| Embedding model | **nomic-embed-text** (274 MB) – Help (RAG) |
| Prompts | the bots' instructions: `modelfiles/Modelfile-*`; assistant: `SYSTEM` in `app/chat/assistant.py`; Help: `SYSTEM` in `app/chat/guide.py` |
| Why this model | given by the task, fits a 4 GB GPU, best published format-calling score of the small models (`docs/submission/model_choice.pdf`) |
| Tested on | Windows 11, 48 GB RAM, NVIDIA GeForce GTX 1650 (4 GB); the model needs about 2.3 GB (GPU or RAM) |

**Install and start the model server:**

```
# install Ollama from https://ollama.com, then:
ollama pull llama3.2:3b
ollama pull nomic-embed-text
ollama create inv-router-bot   -f modelfiles/Modelfile-router
ollama create inv-customer-bot -f modelfiles/Modelfile-customer
ollama create inv-product-bot  -f modelfiles/Modelfile-product
ollama create inv-invoice-bot  -f modelfiles/Modelfile-invoice
```

**Check it:** `ollama list` shows the models; `curl http://localhost:11434/v1/models` answers; the service's
`/health` says `"model_server": "ok"`.

**Replace the model or the server:** any OpenAI-compatible server works (LM Studio, llama.cpp server, …). Set
`LLM_BASE_URL` to its address and `LLM_MODEL` to a model it serves; Python then sends the bots' instructions from
`modelfiles/` itself. Set `LLM_EMBED_MODEL` for Help. No code changes.

## 8. Configuration

All through environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` (Docker: `http://host.docker.internal:11434/v1`) | OpenAI-compatible model server |
| `LLM_MODEL` | empty = the `inv-*` bots | another model for all bots (their instructions are sent by Python) |
| `LLM_TEMPERATURE` | `0` | 0 = the same message always gets the same answer |
| `LLM_TIMEOUT` | `120` | seconds to wait for one model answer, then 503 |
| `LLM_EMBED_MODEL` | `nomic-embed-text` | embedding model for Help |
| `INVOICE_DB_PATH` | `data/invoices.db` (Docker: `/service/data/invoices.db`) | the database file |
| `INVOICE_PYTHON` | `on` | `off` only for the evaluation: the bots without Python's checks and forms |

No credentials or API keys are needed.

## 9. Build, test and start

**Locally** (Python 3.12, tested with fastapi 0.142.2, uvicorn 0.54.0):

```
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000`.

**With Docker** (Ollama runs on the host, see section 7):

```
docker build -t invoice-assistant .
docker run -p 127.0.0.1:8000:8000 -v invoice-data:/service/data invoice-assistant
```

`127.0.0.1:` keeps the service reachable from this computer only. The database lives in the volume
`invoice-data` and survives a rebuild.

**Tests** – each file runs on its own temporary copy of the example data, never on `data/invoices.db`
(PowerShell; most scenarios need the model server):

```
$env:PYTHONPATH = "app"
.\.venv\Scripts\python.exe tests\test_rules.py            # business rules (mostly without AI)
.\.venv\Scripts\python.exe tests\test_customer_lifecycle.py
.\.venv\Scripts\python.exe tests\test_invoice_lifecycle.py
.\.venv\Scripts\python.exe tests\test_answers.py          # answers must match the database
.\.venv\Scripts\python.exe tests\test_understanding.py    # routing
.\.venv\Scripts\python.exe tests\test_conversation.py
.\.venv\Scripts\python.exe tests\test_yes_no.py           # nothing is saved without Yes
.\.venv\Scripts\python.exe tests\test_python.py           # evaluation: bot alone vs bot + Python
.\.venv\Scripts\python.exe tests\test_hangs.py            # timings, model server unreachable (run last)
```

Each scenario prints its exchanges and `##### Scenario …: x/y passed`; the evaluation writes
`tests/results/<date>_python.md`.
What every scenario tests and its last result: [tests/README.md](tests/README.md).

## 10. AI-assisted development and agent sandbox

The project was built with **Claude Code** (CLI, Windows) using **Claude Opus** (Anthropic).

**How the agent was restricted during development:** only by the harness's permission system, not by a sandbox: no
container, no virtual machine, no OS isolation. Commands and file changes needed the user's approval, or ran in auto
mode, where an automatic classifier replaced most prompts. Three commands were allowed without asking in
`.claude/settings.local.json`: `pip list`, `Copy-Item` and `Get-Content`; the last two could reach any folder. The
agent normally worked in the project folder, but nothing enforced this: personal files outside it were reachable, and
once, while looking for the project description in Downloads, the agent listed the names of the PDF files there.
Network access was not restricted, because the agent installs packages and local models.

**Rules from 04/11/2026** (`.claude/settings.json`): auto mode and bypass mode are switched off, the file tools cannot
read or write outside the project, and deleting files, `git push`, `git reset` and `git clean` always ask first. The
two broad commands above are no longer allowed without asking.

**Remaining limits:** these rules do not limit what a shell command can reach, so reviewing each command is still
part of the protection, and the network stays open. A dev container from the start would have been the stronger
choice.

Code changes followed the rule in `CLAUDE.md`: the agent shows each function first and writes it only after the
user's OK. Tests and the website were used to check every change; commits and pushes were made only on the user's
request. No secrets or API keys exist in the project.

Specialised agent roles used during development are described in `.claude/agents/` (entity-builder,
feature-builder, test-writer, acceptance-tester).

## 11. Known limitations

The full list with failure modes, privacy and security: [7_responsible_design.md](docs/submission/7_responsible_design.md).

- The bots do not understand every wording: some messages reach the wrong bot, a new question in the middle
  of a task is not answered – the bot that is waiting replies "Sorry, I can only help with customers" – and bots sometimes ask again for data already given.
- Which form opens is decided by keywords in the bot's question.
- Names are found by exact parts only (a typo finds nothing); unusual names (O'Brien, Müller & Söhne) are not
  handled reliably.
- The bots remember the whole conversation – for a new task, reload the page.
- Conversations live in memory; one local user only (no login), not meant for a network.
- Not an accounting system: no VAT, discounts, partial payments or audit trail.

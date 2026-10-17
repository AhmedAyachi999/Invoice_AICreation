# AI Invoice Assistant

A local invoicing system (customers, products, invoices, turnover) with a chat. The bots (Ollama, llama3.2:3b,
temperature 0) only understand the user; Python looks records up, checks, calculates and saves. The chat never
saves: it returns a proposal, and the website saves it through the CRUD endpoints after the user's "Yes".

## Folders

```
app/          Python code (FastAPI on 127.0.0.1)
  api.py          REST API: CRUD endpoints, reports, chat endpoints, /help, serves the website
  chat/           everything with bots
    router.py       the single chat: the router bot sends each message to a change bot or to the assistant
    assistant.py    questions: the bot with tools (read data, turnover forms, proposals for changes)
    bot.py          talks to Ollama, reads the bot's command, Python guards, converse (change bots)
    guide.py        Help button: answers from docs/user_guide.md (RAG, local embeddings)
  entities/       per entity: checks, lookup by name, create/update/delete, proposal for the chat
    customers.py
    products.py
    invoices.py
  core/           no AI
    reports.py      turnover R1-R3 (paid invoices, by due date)
    storage.py      SQLite: load, save, generate numbers (CUS-001, PRD-001, INV-001)
modelfiles/   the bots: Modelfile-customer, -product, -invoice, -router
static/       the website (one chat, choosers, tables)
tests/        your own tests (empty, starting fresh)
docs/         requirements, architecture, model choice, test scenarios (PDF), user_guide.md (Help),
              open_problems.md, test_plan.md, code_check_plan.pdf
data/         the database invoices.db (created on first start, not in git)
```

## Setup

```
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
ollama pull llama3.2:3b
ollama create inv-customer-bot -f modelfiles/Modelfile-customer
ollama create inv-product-bot  -f modelfiles/Modelfile-product
ollama create inv-invoice-bot  -f modelfiles/Modelfile-invoice
ollama create inv-router-bot   -f modelfiles/Modelfile-router
```

## Start

```
.\.venv\Scripts\python.exe -m uvicorn api:app --app-dir app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:8000 (website) or http://127.0.0.1:8000/docs (all endpoints).

## Endpoints

| Endpoint | Purpose | AI |
|---|---|---|
| `POST /chat` | The single chat used by the website (router -> change bot or assistant) | yes |
| `POST /customers/chat`, `/products/chat`, `/invoices/chat` | Chat with one change bot directly | yes |
| `POST /assistant/chat` | Chat with the assistant directly | yes |
| `GET/POST/PUT/DELETE /customers`, `/products`, `/invoices` | CRUD; checks again before saving | no |
| `GET /reports/customers?start&end`, `/reports/products?start&end`, `/reports/months?year` | Turnover R1-R3 | no |

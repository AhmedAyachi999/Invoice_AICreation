"""The REST API (FastAPI, only on 127.0.0.1): the Python hub of the architecture. Every request enters here.

The endpoints are grouped by what they are allowed to do:
  1. Request models  - what a request body must contain (FastAPI checks it, else 422)
  2. READ            - GET endpoints: return data, never change anything
  3. WRITE           - POST / PUT / DELETE: the ONLY place that saves; the client calls them after the user's "Yes"
  4. CHAT            - the bots: they only answer or return a proposal, they NEVER save
  5. Website         - serves static/ (must stay last)
api.py itself checks and calculates nothing: it calls the modules and turns their errors into HTTP answers.
"""
import sqlite3
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from chat import assistant, bot, guide, router
from core import reports, storage
from entities import customers, invoices, products

app = FastAPI(title="AI Invoice Assistant")
storage.seed()  # first start: the example data from seed/demo_data.json


@app.exception_handler(bot.ModelError)
def model_error(request: Request, error: bot.ModelError):
    """The language model is down, too slow or answered nonsense: 503 with a clear message (CRUD still works)."""
    return JSONResponse(status_code=503, content={"detail": str(error)})


@app.exception_handler(sqlite3.Error)
def database_error(request: Request, error: sqlite3.Error):
    """The database cannot be read or written: 503 with a clear message instead of a crash."""
    return JSONResponse(status_code=503,
                        content={"detail": "The database cannot be read or written. Please try again."})


# ===================================================================================================================
# 1. REQUEST MODELS
# What a request body must look like. When an endpoint has a parameter "data: CustomerIn", FastAPI reads the JSON
# body, checks the fields and types, and answers 422 by itself if something is missing - before the function runs.
# ===================================================================================================================

class CustomerIn(BaseModel):
    """The data a client sends to create or change a customer."""
    name: str
    address: str


class ProductIn(BaseModel):
    """The data a client sends to create or change a product. The price may be a number or text like "12,5"."""
    name: str
    sell_price: float | str


class LineIn(BaseModel):
    """One invoice line. Without unit_price the product's sell_price is used."""
    product_id: str
    quantity: int | float | str
    unit_price: float | str | None = None


class InvoiceIn(BaseModel):
    """The data a client sends to create or change an invoice. Dates are DD/MM/YYYY, status paid or unpaid."""
    customer_id: str
    date: str
    due_date: str
    status: str
    lines: list[LineIn]


class ChatIn(BaseModel):
    """One chat message from the frontend. conversation_id is empty on the first message."""
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class ErrorOut(BaseModel):
    """The body of every error answer (400, 404, 503), e.g. {"detail": "Customer CUS-999 not found"}."""
    detail: str


def errors(codes):
    """The error answers of an endpoint for the API docs (/docs): {404: "why"} -> {404: {model, description}}."""
    codes = {503: "The database is not available", **codes}  # every endpoint reads or writes the database
    return {code: {"model": ErrorOut, "description": text} for code, text in codes.items()}


# ===================================================================================================================
# 2. READ - never changes anything
# Lists, single records (404 if the number doesn't exist) and the turnover reports R1-R3 (calculated by Python in
# reports.py; turnover = paid invoices, counted by due date). No AI.
# ===================================================================================================================

@app.get("/health", responses=errors({503: "The database cannot be read"}))
def health():
    """Is the service OK? The database must work (else 503); without the model server only the chat is down (degraded)."""
    try:
        storage.load("customers")
    except sqlite3.Error:
        raise HTTPException(503, "The database cannot be read.")
    model_server = "ok" if bot.server_ok() else "unreachable"
    return {"status": "ok" if model_server == "ok" else "degraded", "database": "ok", "model_server": model_server}


@app.get("/customers")
def list_customers():
    """Return all customers."""
    return storage.load("customers")


@app.get("/customers/{customer_id}", responses=errors({404: "No customer with this number"}))
def get_customer(customer_id: str):
    """Return one customer, or 404 if the number doesn't exist."""
    customer = storage.find(storage.load("customers"), customer_id)
    if customer is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return customer


@app.get("/products")
def list_products():
    """Return all products."""
    return storage.load("products")


@app.get("/products/{product_id}", responses=errors({404: "No product with this number"}))
def get_product(product_id: str):
    """Return one product, or 404 if the code doesn't exist."""
    product = storage.find(storage.load("products"), product_id)
    if product is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return product


@app.get("/invoices")
def list_invoices():
    """Return all invoices, each with its total."""
    return [{**invoice, "total": invoices.invoice_total(invoice)} for invoice in storage.load("invoices")]


@app.get("/invoices/{invoice_id}", responses=errors({404: "No invoice with this number"}))
def get_invoice(invoice_id: str):
    """Return one invoice with its lines and total, or 404 if the number doesn't exist."""
    invoice = storage.find(storage.load("invoices"), invoice_id)
    if invoice is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    return {**invoice, "total": invoices.invoice_total(invoice)}


@app.get("/reports/customers", responses=errors({400: "The period is not valid (dates DD/MM/YYYY, start before end)"}))
def report_customers(start: str, end: str):
    """R1: turnover per customer between start and end (DD/MM/YYYY, query parameters), or 400 if the period is not valid."""
    error = reports.check_period(start, end)
    if error:
        raise HTTPException(400, error)
    return reports.turnover_by_customer(start, end)


@app.get("/reports/products", responses=errors({400: "The period is not valid (dates DD/MM/YYYY, start before end)"}))
def report_products(start: str, end: str):
    """R2: turnover and quantity per product between start and end (DD/MM/YYYY, query parameters), or 400 if the period is not valid."""
    error = reports.check_period(start, end)
    if error:
        raise HTTPException(400, error)
    return reports.turnover_by_product(start, end)


@app.get("/reports/months",
         responses=errors({400: "The year is not a 4-digit year", 404: "No customer or product with this number"}))
def report_months(year: str, customer_id: str | None = None, product_id: str | None = None):
    """R3: turnover for each month of a year, optionally for one customer and/or one product (by number).
    400 if the year is not valid, 404 if the customer or product doesn't exist."""
    if invoices.to_date(f"01/01/{year}") is None:
        raise HTTPException(400, f"The year must be a 4-digit year like 2026, not '{year}'.")
    if customer_id and storage.find(storage.load("customers"), customer_id) is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    if product_id and storage.find(storage.load("products"), product_id) is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return reports.turnover_by_month(year, customer_id, product_id)


# ===================================================================================================================
# 3. WRITE - the only place that saves
# Called by the client after the user said "Yes" to a proposal (or directly by another program). Every write checks
# the data AGAIN with the same functions the chat used, because the data may have changed since the proposal
# (risk RK22): 400 = the data is not valid, 404 = the number doesn't exist. Python assigns the numbers.
# ===================================================================================================================

@app.post("/customers", status_code=201,
          responses=errors({400: "The data is not valid (e.g. the name or address is missing)"}))
def add_customer(data: CustomerIn):
    """Create a customer and return it with its new number, or 400 if the data is not valid."""
    error = customers.check_customer(data.model_dump())
    if error:
        raise HTTPException(400, error)
    return customers.create_customer(data.model_dump())


@app.put("/customers/{customer_id}",
         responses=errors({400: "The data is not valid", 404: "No customer with this number"}))
def change_customer(customer_id: str, data: CustomerIn):
    """Change name and address of a customer: 404 if the number doesn't exist, 400 if the data is not valid."""
    error = customers.check_customer(data.model_dump())
    if error:
        raise HTTPException(400, error)
    customer = customers.update_customer(customer_id, data.model_dump())
    if customer is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return customer


@app.delete("/customers/{customer_id}",
            responses=errors({400: "The customer is used in invoices", 404: "No customer with this number"}))
def remove_customer(customer_id: str):
    """Delete a customer: 404 if the number doesn't exist, 400 if it still has invoices."""
    try:
        customer = customers.delete_customer(customer_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if customer is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return customer


@app.post("/products", status_code=201,
          responses=errors({400: "The data is not valid (e.g. the price is missing or negative)"}))
def add_product(data: ProductIn):
    """Create a product and return it with its new code, or 400 if the data is not valid."""
    error = products.check_product(data.model_dump())
    if error:
        raise HTTPException(400, error)
    return products.create_product(data.model_dump())


@app.put("/products/{product_id}", responses=errors({400: "The data is not valid", 404: "No product with this number"}))
def change_product(product_id: str, data: ProductIn):
    """Change name and prices of a product: 404 if the code doesn't exist, 400 if the data is not valid."""
    error = products.check_product(data.model_dump())
    if error:
        raise HTTPException(400, error)
    product = products.update_product(product_id, data.model_dump())
    if product is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return product


@app.delete("/products/{product_id}",
            responses=errors({400: "The product is used in an invoice", 404: "No product with this number"}))
def remove_product(product_id: str):
    """Delete a product: 404 if the code doesn't exist, 400 if an invoice line uses it."""
    try:
        product = products.delete_product(product_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if product is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return product


@app.post("/invoices", status_code=201,
          responses=errors({400: "The data is not valid (e.g. unknown customer or product, wrong date)"}))
def add_invoice(data: InvoiceIn):
    """Create an invoice and return it with its new number and total, or 400 if the data is not valid."""
    error = invoices.check_invoice(data.model_dump())
    if error:
        raise HTTPException(400, error)
    invoice = invoices.create_invoice(data.model_dump())
    return {**invoice, "total": invoices.invoice_total(invoice)}


@app.put("/invoices/{invoice_id}", responses=errors({400: "The data is not valid", 404: "No invoice with this number"}))
def change_invoice(invoice_id: str, data: InvoiceIn):
    """Change an invoice: 404 if the number doesn't exist, 400 if the data is not valid."""
    if storage.find(storage.load("invoices"), invoice_id) is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    error = invoices.check_invoice(data.model_dump())
    if error:
        raise HTTPException(400, error)
    invoice = invoices.update_invoice(invoice_id, data.model_dump())
    return {**invoice, "total": invoices.invoice_total(invoice)}


@app.delete("/invoices/{invoice_id}",
            responses=errors({400: "The invoice is paid", 404: "No invoice with this number"}))
def remove_invoice(invoice_id: str):
    """Delete an invoice: 404 if the number doesn't exist, 400 if it is paid."""
    try:
        invoice = invoices.delete_invoice(invoice_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if invoice is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    return invoice


# ===================================================================================================================
# 4. CHAT - the bots, never save
# Each call is one message of a conversation (kept on the server by conversation_id). The answer is either a reply
# (a question, an error, an answer with data) or a checked proposal {method, path, body, summary} that the client
# shows with Yes / No; on "Yes" the client calls the matching WRITE endpoint above.
#   /chat              the single chat of the website: router.py picks the bot for each message
#   /<entity>/chat     one change bot directly; bot.converse gets that entity's check / proposal / answer functions
#   /assistant/chat    the assistant with tools (questions, turnover forms) directly
# ===================================================================================================================

@app.post("/chat", responses=errors({503: "The language model or the database is not available"}))
def chat(data: ChatIn):
    """The single chat: the router sends the message to the customer, product or invoice bot or to the assistant.
    Never saves."""
    return router.converse(data.conversation_id, data.message)


@app.post("/customers/chat", responses=errors({503: "The language model or the database is not available"}))
def customer_chat(data: ChatIn):
    """Send one message to the customer bot. Returns its question, or a proposal to confirm. Never saves."""
    return bot.converse("inv-customer-bot", customers.check_command, customers.build_proposal, customers.answer,
                        data.conversation_id, data.message)


@app.post("/products/chat", responses=errors({503: "The language model or the database is not available"}))
def product_chat(data: ChatIn):
    """Send one message to the product bot. Returns its question, or a proposal to confirm. Never saves."""
    return bot.converse("inv-product-bot", products.check_command, products.build_proposal, products.answer,
                        data.conversation_id, data.message)


@app.post("/invoices/chat", responses=errors({503: "The language model or the database is not available"}))
def invoice_chat(data: ChatIn):
    """Send one message to the invoice bot. Returns its question, or a proposal to confirm. Never saves."""
    return bot.converse("inv-invoice-bot", invoices.check_command, invoices.build_proposal, invoices.answer,
                        data.conversation_id, data.message)


@app.post("/assistant/chat", responses=errors({503: "The language model or the database is not available"}))
def assistant_chat(data: ChatIn):
    """Ask the assistant (bot with tools). Returns its answer, or a proposal to confirm. Never saves."""
    return assistant.converse(data.conversation_id, data.message)


@app.post("/help", responses=errors({503: "The language model or the database is not available"}))
def help_chat(data: ChatIn):
    """Answer a question about using the software from the user guide (RAG, guide.py). Never saves."""
    return {"reply": guide.answer(data.message)}


# ===================================================================================================================
# 5. WEBSITE
# Must stay last: serves the frontend (static/) at "/" after all API endpoints were matched.
# ===================================================================================================================

app.mount("/", StaticFiles(directory=Path(__file__).parent.parent / "static", html=True), name="static")

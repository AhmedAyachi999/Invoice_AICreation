from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import bot
import customers
import invoices
import products
import storage

app = FastAPI(title="AI Invoice Assistant")


class CustomerIn(BaseModel):
    """The data a client sends to create or change a customer."""
    name: str
    address: str


class ProductIn(BaseModel):
    """The data a client sends to create or change a product. Prices may be numbers or text like "12,5"."""
    name: str
    sell_price: float | str
    buy_price: float | str | None = None


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
    message: str
    conversation_id: str | None = None


@app.get("/customers")
def list_customers():
    """Return all customers."""
    return storage.load("customers")


@app.get("/customers/{customer_id}")
def get_customer(customer_id: str):
    """Return one customer, or 404 if the number doesn't exist."""
    customer = storage.find(storage.load("customers"), customer_id)
    if customer is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return customer


@app.post("/customers", status_code=201)
def add_customer(data: CustomerIn):
    """Create a customer and return it with its new number."""
    return customers.create_customer(data.model_dump())


@app.put("/customers/{customer_id}")
def change_customer(customer_id: str, data: CustomerIn):
    """Change name and address of a customer, or 404 if the number doesn't exist."""
    customer = customers.update_customer(customer_id, data.model_dump())
    if customer is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return customer


@app.delete("/customers/{customer_id}")
def remove_customer(customer_id: str):
    """Delete a customer: 404 if the number doesn't exist, 400 if it still has invoices."""
    try:
        customer = customers.delete_customer(customer_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if customer is None:
        raise HTTPException(404, f"Customer {customer_id} not found")
    return customer


@app.post("/customers/chat")
def customer_chat(data: ChatIn):
    """Send one message to the customer bot. Returns its question, or a proposal to confirm. Never saves."""
    return bot.converse("inv-customer-bot", customers.check_command, customers.build_proposal,
                        data.conversation_id, data.message)


@app.get("/products")
def list_products():
    """Return all products."""
    return storage.load("products")


@app.get("/products/{product_id}")
def get_product(product_id: str):
    """Return one product, or 404 if the code doesn't exist."""
    product = storage.find(storage.load("products"), product_id)
    if product is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return product


@app.post("/products", status_code=201)
def add_product(data: ProductIn):
    """Create a product and return it with its new code, or 400 if the data is not valid."""
    error = products.check_product(data.model_dump())
    if error:
        raise HTTPException(400, error)
    return products.create_product(data.model_dump())


@app.put("/products/{product_id}")
def change_product(product_id: str, data: ProductIn):
    """Change name and prices of a product: 404 if the code doesn't exist, 400 if the data is not valid."""
    error = products.check_product(data.model_dump())
    if error:
        raise HTTPException(400, error)
    product = products.update_product(product_id, data.model_dump())
    if product is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return product


@app.delete("/products/{product_id}")
def remove_product(product_id: str):
    """Delete a product: 404 if the code doesn't exist, 400 if an invoice line uses it."""
    try:
        product = products.delete_product(product_id)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if product is None:
        raise HTTPException(404, f"Product {product_id} not found")
    return product


@app.post("/products/chat")
def product_chat(data: ChatIn):
    """Send one message to the product bot. Returns its question, or a proposal to confirm. Never saves."""
    return bot.converse("inv-product-bot", products.check_command, products.build_proposal,
                        data.conversation_id, data.message)


@app.get("/invoices")
def list_invoices():
    """Return all invoices."""
    return storage.load("invoices")


@app.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str):
    """Return one invoice with its lines and total, or 404 if the number doesn't exist."""
    invoice = storage.find(storage.load("invoices"), invoice_id)
    if invoice is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    return {**invoice, "total": invoices.invoice_total(invoice)}


@app.post("/invoices", status_code=201)
def add_invoice(data: InvoiceIn):
    """Create an invoice and return it with its new number and total, or 400 if the data is not valid."""
    error = invoices.check_invoice(data.model_dump())
    if error:
        raise HTTPException(400, error)
    invoice = invoices.create_invoice(data.model_dump())
    return {**invoice, "total": invoices.invoice_total(invoice)}


@app.put("/invoices/{invoice_id}")
def change_invoice(invoice_id: str, data: InvoiceIn):
    """Change an invoice: 404 if the number doesn't exist, 400 if the data is not valid."""
    if storage.find(storage.load("invoices"), invoice_id) is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    error = invoices.check_invoice(data.model_dump())
    if error:
        raise HTTPException(400, error)
    invoice = invoices.update_invoice(invoice_id, data.model_dump())
    return {**invoice, "total": invoices.invoice_total(invoice)}


@app.delete("/invoices/{invoice_id}")
def remove_invoice(invoice_id: str):
    """Delete an invoice, or 404 if the number doesn't exist."""
    invoice = invoices.delete_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(404, f"Invoice {invoice_id} not found")
    return invoice


@app.post("/invoices/chat")
def invoice_chat(data: ChatIn):
    """Send one message to the invoice bot. Returns its question, or a proposal to confirm. Never saves."""
    return bot.converse("inv-invoice-bot", invoices.check_command, invoices.build_proposal,
                        data.conversation_id, data.message)

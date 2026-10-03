from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import customers
import invoices
import storage

app = FastAPI(title="AI Invoice Assistant")


class CustomerIn(BaseModel):
    """The data a client sends to create or change a customer."""
    name: str
    address: str


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

"""The assistant: llama3.2:3b with tools. Read tools are answered by Python at once; write tools are only checked
and returned as a proposal, which the frontend saves through the CRUD endpoints after the user's yes."""
import calendar
import json
import urllib.request

import customers
import invoices
import products
import reports
import storage
from bot import OLLAMA_URL, get_conversation

MODEL = "llama3.2:3b"
MAX_ROUNDS = 5  # tool calls per user message before the bot has to answer
SYSTEM = ("You help with the customers, products, invoices and turnover of an invoicing system. Use the tools to "
          "read data and answer only from what they return. Dates are DD/MM/YYYY. Turnover means paid invoices, "
          "counted by due date. Records are changed only with the create_/update_/delete_ tools, which ask the user "
          "to confirm first; never say that something was saved before the user confirmed. "
          "Write every answer in three parts:\n"
          "Answer: the result.\n"
          "Input: what you used - the user's question or the values from the form, and which data the tools "
          "returned (how many records, which ones mattered).\n"
          "Analysis: how you got the result from that input, step by step - what you filtered, matched, counted or "
          "added.\n\n"
          "Think step by step: what does the user want, what do I need first, which tool gives it. Then call the "
          "tools one after the other and wait for each result.\n\n"
          "Turnover questions always go through a form unless the user wrote the period: call ask_turnover_period "
          "(per customer), ask_product_turnover_period (per product) or ask_monthly_turnover (month by month). The "
          "user's answer from the form is always correct: accept it exactly, never change it and never ask again.\n"
          "If a period was already given earlier in this conversation (typed or from a form), use the same period "
          "for follow-up questions like sorting or showing it per product; do not call a form again.\n"
          "'all customers' and 'all products' mean no filter: leave customer_id and product_id out.\n"
          "When you have a period and a customer (one customer or all customers), answer directly with "
          "get_turnover_by_customer: do not ask about products and do not call another form. If the form names a "
          "customer, pass its id in brackets as customer_id; if it names a product, pass its id in brackets as "
          "product_id. Never make up an id. The tool's last row is the Total: copy it, never add up yourself.\n\n"
          "The examples below use made-up names, numbers and dates. Never use them in an answer.\n\n"
          "Example 1:\n"
          "User: which products did Mara Quist buy?\n"
          "Assistant calls get_customers()\n"
          "Tool: [{\"id\": \"CUS-047\", \"name\": \"Mara Quist\", \"address\": \"Hafenweg 3, 20457 Hamburg\"}, ...]\n"
          "Assistant calls get_invoices()\n"
          "Tool: [{\"id\": \"INV-640\", \"customer_id\": \"CUS-047\", \"lines\": [{\"product_id\": \"PRD-031\", "
          "\"quantity\": 2}], ...}, ...]\n"
          "Assistant calls get_products()\n"
          "Tool: [{\"id\": \"PRD-031\", \"name\": \"Copper Kettle\", ...}, ...]\n"
          "Assistant: Answer: Mara Quist bought 2 Copper Kettle (invoice INV-640).\n"
          "Input: the question about Mara Quist; the customers, the invoices and the products from the tools.\n"
          "Analysis: 1. In the customers, Mara Quist has the id CUS-047. 2. Of the invoices, only INV-640 has "
          "customer_id CUS-047. 3. Its line has product PRD-031 with quantity 2. 4. In the products, PRD-031 is the "
          "Copper Kettle.\n\n"
          "Example 2:\n"
          "User: how much turnover did we make per customer?\n"
          "Assistant calls ask_turnover_period()\n"
          "User: turnover from 01/03/2031 to 31/03/2031, all customers, all products\n"
          "Assistant calls get_turnover_by_customer(start=\"01/03/2031\", end=\"31/03/2031\")\n"
          "Tool: [{\"customer_id\": \"CUS-047\", \"name\": \"Mara Quist\", \"turnover\": 120.0}, "
          "{\"customer_id\": \"CUS-052\", \"name\": \"Ole Brandt\", \"turnover\": 80.0}, "
          "{\"name\": \"Total\", \"turnover\": 200.0}]\n"
          "Assistant: Answer: from 01/03/2031 to 31/03/2031: Mara Quist 120.00, Ole Brandt 80.00, total 200.00.\n"
          "Input: from the form the period 01/03/2031 to 31/03/2031 and all customers; the tool returned 2 customers "
          "with turnover (paid invoices, by due date) and the total.\n"
          "Analysis: I listed both customers with their turnover and copied the total.\n\n"
          "Example 2a:\n"
          "User: turnover of one customer\n"
          "Assistant calls ask_turnover_period()\n"
          "User: turnover from 01/03/2031 to 31/03/2031, customer: Ole Brandt (CUS-052), all products\n"
          "Assistant calls get_turnover_by_customer(start=\"01/03/2031\", end=\"31/03/2031\", customer_id=\"CUS-052\")\n"
          "Tool: [{\"customer_id\": \"CUS-052\", \"name\": \"Ole Brandt\", \"turnover\": 80.0}, "
          "{\"name\": \"Total\", \"turnover\": 80.0}]\n"
          "Assistant: Answer: from 01/03/2031 to 31/03/2031 Ole Brandt's turnover was 80.00.\n"
          "Input: from the form the period 01/03/2031 to 31/03/2031 and the customer Ole Brandt with the id CUS-052; "
          "the tool returned only that customer.\n"
          "Analysis: I passed the id from the form, so the tool returned only Ole Brandt; I copied his turnover.\n\n"
          "Example 2b:\n"
          "User: turnover per customer for one product\n"
          "Assistant calls ask_turnover_period()\n"
          "User: turnover from 01/03/2031 to 31/03/2031, all customers, product: Copper Kettle (PRD-031)\n"
          "Assistant calls get_turnover_by_customer(start=\"01/03/2031\", end=\"31/03/2031\", product_id=\"PRD-031\")\n"
          "Tool: [{\"customer_id\": \"CUS-047\", \"name\": \"Mara Quist\", \"turnover\": 49.8}, "
          "{\"name\": \"Total\", \"turnover\": 49.8}]\n"
          "Assistant: Answer: from 01/03/2031 to 31/03/2031 the Copper Kettle earned 49.80, all with Mara Quist.\n"
          "Input: from the form the period 01/03/2031 to 31/03/2031, all customers and the product Copper Kettle "
          "(PRD-031); the tool returned 1 customer.\n"
          "Analysis: only the Copper Kettle lines were counted; Mara Quist is the only customer who bought it in "
          "this period.\n\n"
          "Example 3:\n"
          "User: how did the Copper Kettle sell?\n"
          "Assistant calls ask_product_turnover_period()\n"
          "User: product turnover from 01/03/2031 to 31/03/2031, product: Copper Kettle\n"
          "Assistant calls get_turnover_by_product(start=\"01/03/2031\", end=\"31/03/2031\")\n"
          "Tool: [{\"product_id\": \"PRD-031\", \"name\": \"Copper Kettle\", \"quantity\": 2, \"turnover\": 49.8}]\n"
          "Assistant: Answer: from 01/03/2031 to 31/03/2031 the Copper Kettle earned 49.80 (2 sold).\n"
          "Input: from the form the period 01/03/2031 to 31/03/2031 and the product Copper Kettle; the tool returned "
          "1 product with turnover.\n"
          "Analysis: I took the line of the Copper Kettle from the result. (If a product is not in the result, it "
          "earned 0.00.)\n\n"
          "Example 4:\n"
          "User: show me the turnover per month\n"
          "Assistant calls ask_monthly_turnover()\n"
          "User: monthly turnover for 2031, customer: Mara Quist (CUS-047), all products\n"
          "Assistant calls get_turnover_by_month(year=\"2031\", customer_id=\"CUS-047\")\n"
          "Tool: [{\"month\": \"January\", \"turnover\": 0}, ..., {\"month\": \"March\", \"turnover\": 120.0}, ..., "
          "{\"month\": \"December\", \"turnover\": 0}, {\"month\": \"Total\", \"turnover\": 120.0}]\n"
          "Assistant: Answer: turnover of Mara Quist in 2031: January 0.00, February 0.00, March 120.00, April 0.00, "
          "May 0.00, June 0.00, July 0.00, August 0.00, September 0.00, October 0.00, November 0.00, December 0.00. "
          "Total 120.00.\n"
          "Input: from the form the year 2031, the customer Mara Quist with the id CUS-047 and all products; the "
          "tool returned the 12 months and the total.\n"
          "Analysis: I copied each month and the total exactly as the tool returned them; only March has turnover.\n\n"
          "Example 5 (a follow-up after Example 2, same conversation):\n"
          "User: now show it per product\n"
          "Assistant calls get_turnover_by_product(start=\"01/03/2031\", end=\"31/03/2031\")\n"
          "Tool: [{\"product_id\": \"PRD-031\", \"name\": \"Copper Kettle\", \"quantity\": 2, \"turnover\": 49.8}, "
          "{\"product_id\": \"PRD-036\", \"name\": \"Linen Apron\", \"quantity\": 10, \"turnover\": 150.2}]\n"
          "Assistant: Answer: from 01/03/2031 to 31/03/2031: Linen Apron 150.20 (10 sold), Copper Kettle 49.80 "
          "(2 sold), total 200.00.\n"
          "Input: the same period as before, 01/03/2031 to 31/03/2031, so no form was needed; the tool returned 2 "
          "products.\n"
          "Analysis: I listed the products from the highest turnover down and added 150.20 + 49.80 = 200.00.\n\n"
          "Example 6:\n"
          "User: monthly turnover for all customers and all products\n"
          "Assistant calls ask_monthly_turnover()\n"
          "User: monthly turnover for 2031, all customers, all products\n"
          "Assistant calls get_turnover_by_month(year=\"2031\")\n"
          "Tool: [{\"month\": \"January\", \"turnover\": 0}, ..., {\"month\": \"March\", \"turnover\": 200.0}, ..., "
          "{\"month\": \"December\", \"turnover\": 0}, {\"month\": \"Total\", \"turnover\": 200.0}]\n"
          "Assistant: Answer: turnover in 2031, all customers and all products: January 0.00, February 0.00, March "
          "200.00, April 0.00, May 0.00, June 0.00, July 0.00, August 0.00, September 0.00, October 0.00, November "
          "0.00, December 0.00. Total 200.00.\n"
          "Input: from the form the year 2031 with no customer and no product filter; the tool returned the 12 months "
          "and the total.\n"
          "Analysis: 'all customers' and 'all products' mean no filter, so I called the tool with the year only and "
          "copied each month and the total.")


def tool(name, description, properties=None, required=()):
    """One tool definition in Ollama's format."""
    return {"type": "function", "function": {"name": name, "description": description, "parameters": {
        "type": "object", "properties": properties or {}, "required": list(required)}}}


TEXT, NUMBER = {"type": "string"}, {"type": "number"}
CUSTOMER_ID = {"type": "string", "description": "The id of the customer. Call get_customers first and take the "
                                                "id of that customer from its result. Never guess an id."}
PRODUCT_ID = {"type": "string", "description": "The id of the product. Call get_products first and take the "
                                              "id of that product from its result. Never guess an id."}
INVOICE_ID = {"type": "string", "description": "The id of the invoice: the invoice number the user wrote, or call "
                                              "get_invoices first and take the id from its result. Never guess an id."}
LINES = {"type": "array", "items": {"type": "object", "properties": {
    "product_id": PRODUCT_ID, "quantity": NUMBER, "unit_price": NUMBER}}}
INVOICE = {"customer_id": CUSTOMER_ID, "date": TEXT, "due_date": TEXT, "status": TEXT, "lines": LINES}
PERIOD = {"start": TEXT, "end": TEXT, "month": NUMBER, "year": TEXT}
TOOLS = [
    tool("ask_turnover_period", "Show the user a form to choose the start date, the end date and optionally one "
         "customer for a turnover question. Use it when the user did not write both dates."),
    tool("ask_product_turnover_period", "Show the user a form to choose the start date, the end date and optionally "
         "one product for a question about turnover per product. Use it when the user did not write both dates."),
    tool("ask_monthly_turnover", "Show the user a form to choose a year and optionally a customer and a product for "
         "a question about turnover month by month. Use it when the user did not write a year."),
    tool("get_customers", "All customers: id, name, address."),
    tool("get_products", "All products: id, name, sell_price, buy_price."),
    tool("get_invoices", "All invoices: id, customer_id, date, due_date, status (paid/unpaid), lines, total."),
    tool("get_turnover_by_customer", "Turnover per customer in a period: give start and end dates, or a month "
         "(1-12) and/or a year. No period means the current year. With customer_id only that customer is returned; "
         "with product_id only that product counts. The last row is the Total.",
         {**PERIOD, "customer_id": CUSTOMER_ID, "product_id": PRODUCT_ID}),
    tool("get_turnover_by_product", "Turnover per product in a period: give start and end dates, or a month "
         "(1-12) and/or a year. No period means the current year.", PERIOD),
    tool("get_turnover_by_month", "Turnover per month of a year, optionally for one customer or product.",
         {"year": TEXT, "customer_id": CUSTOMER_ID, "product_id": PRODUCT_ID}, ["year"]),
    tool("create_customer", "Propose a new customer.", {"name": TEXT, "address": TEXT}, ["name", "address"]),
    tool("update_customer", "Propose changing a customer.", {"customer_id": CUSTOMER_ID, "name": TEXT, "address": TEXT},
         ["customer_id", "name", "address"]),
    tool("delete_customer", "Propose deleting a customer.", {"customer_id": CUSTOMER_ID}, ["customer_id"]),
    tool("create_product", "Propose a new product.", {"name": TEXT, "sell_price": NUMBER, "buy_price": NUMBER},
         ["name", "sell_price"]),
    tool("update_product", "Propose changing a product.",
         {"product_id": PRODUCT_ID, "name": TEXT, "sell_price": NUMBER, "buy_price": NUMBER},
         ["product_id", "name", "sell_price"]),
    tool("delete_product", "Propose deleting a product.", {"product_id": PRODUCT_ID}, ["product_id"]),
    tool("create_invoice", "Propose a new invoice.", INVOICE, list(INVOICE)),
    tool("update_invoice", "Propose changing an invoice.", {"invoice_id": INVOICE_ID, **INVOICE}, ["invoice_id", *INVOICE]),
    tool("delete_invoice", "Propose deleting an invoice.", {"invoice_id": INVOICE_ID}, ["invoice_id"]),
]
UI_TOOLS = {  # tool name -> (form the browser shows, text shown with it)
    "ask_turnover_period": ("turnover", "Please choose the period and, if you want, one customer."),
    "ask_product_turnover_period": ("product_turnover", "Please choose the period and, if you want, one product."),
    "ask_monthly_turnover": ("monthly_turnover", "Please choose the year and, if you want, a customer and a product."),
}
FORM_FOR = {  # turnover tool -> the UI tool Python shows instead when the period does not come from the user
    "get_turnover_by_customer": "ask_turnover_period",
    "get_turnover_by_product": "ask_product_turnover_period",
    "get_turnover_by_month": "ask_monthly_turnover",
}
CHECKS = {"customer": customers.check_customer, "product": products.check_product, "invoice": invoices.check_invoice}


def chat(messages):
    """Send the conversation and the tools to Ollama; return the bot's message (text and/or tool calls)."""
    body = json.dumps({"model": MODEL, "messages": messages, "tools": TOOLS, "stream": False,
                       "options": {"temperature": 0}}).encode()
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())["message"]


def period_from_user(name, args, messages):
    """True if the period of a turnover tool call was written by the user (in a message or through a form).
    Dates (start and end) or a year must appear literally in the user's messages; else Python shows the form."""
    said = " ".join(m["content"] for m in messages if m["role"] == "user").lower()
    dates = [str(args.get(key) or "").strip().lower() for key in ("start", "end")]
    values = dates if name != "get_turnover_by_month" and all(dates) else [str(args.get("year") or "").strip().lower()]
    return all(values) and all(value in said for value in values)


def read(name, args):
    """Answer a read tool from the database (Python calculates totals and turnover)."""
    if name == "get_customers":
        return storage.load("customers")
    if name == "get_products":
        return storage.load("products")
    if name == "get_invoices":
        return [{**i, "total": invoices.invoice_total(i)} for i in storage.load("invoices")]
    if name == "get_turnover_by_month":
        year = str(args.get("year", "")).strip()
        if invoices.to_date(f"01/01/{year}") is None:
            return {"error": f"The year must be a 4-digit year like 2026, not '{year}'."}
        customer_id, product_id = (str(args.get(key) or "").strip().upper() for key in ("customer_id", "product_id"))
        customer_id = None if customer_id in ("", "ALL", "ALL CUSTOMERS") else customer_id  # the form's "no filter"
        product_id = None if product_id in ("", "ALL", "ALL PRODUCTS") else product_id
        if customer_id and storage.find(storage.load("customers"), customer_id) is None:
            return {"error": f"There is no customer {customer_id}. Take the id from get_customers."}
        if product_id and storage.find(storage.load("products"), product_id) is None:
            return {"error": f"There is no product {product_id}. Take the id from get_products."}
        rows = reports.turnover_by_month(year, customer_id, product_id)
        total = round(sum(row["turnover"] for row in rows), 2)
        return [{"month": calendar.month_name[row["month"]], "turnover": row["turnover"]} for row in rows] + \
               [{"month": "Total", "turnover": total}]
    start, end = reports.period(args)  # dates as given, or month/year turned into the first and last day by Python
    error = reports.check_period(start, end)
    if error:
        return {"error": error}
    if name == "get_turnover_by_customer":
        customer_id, product_id = (str(args.get(key) or "").strip().upper() for key in ("customer_id", "product_id"))
        customer_id = None if customer_id in ("", "ALL", "ALL CUSTOMERS") else customer_id  # the form's "no filter"
        product_id = None if product_id in ("", "ALL", "ALL PRODUCTS") else product_id
        customer = storage.find(storage.load("customers"), customer_id) if customer_id else None
        if customer_id and customer is None:
            return {"error": f"There is no customer {customer_id}. Take the id from get_customers."}
        if product_id and storage.find(storage.load("products"), product_id) is None:
            return {"error": f"There is no product {product_id}. Take the id from get_products."}
        rows = reports.turnover_by_customer(start, end, product_id)
        if customer:  # one customer: only that row, 0.00 if the customer had no turnover
            rows = [r for r in rows if r["customer_id"] == customer_id] or \
                   [{"customer_id": customer_id, "name": customer["name"], "turnover": 0.0}]
        return rows + [{"name": "Total", "turnover": round(sum(r["turnover"] for r in rows), 2)}]
    return reports.turnover_by_product(start, end)


def propose(name, args):
    """Check a write tool call with our Python checks. Return (error, None) or (None, proposal) - never saves."""
    action, _, entity = name.partition("_")
    if action not in ("create", "update", "delete") or entity not in CHECKS:
        return f"There is no tool {name}.", None
    args = dict(args)
    plural = entity + "s"
    record_id = str(args.pop(f"{entity}_id", "")).strip().upper()
    old = storage.find(storage.load(plural), record_id) if record_id else None
    if action != "create" and old is None:
        return f"There is no {entity} {record_id}.", None
    if action != "delete":
        error = CHECKS[entity](args)
        if error:
            return error, None
    method = {"create": "POST", "update": "PUT", "delete": "DELETE"}[action]
    body = None if action == "delete" else args
    label = f" {record_id} ({old.get('name') or old.get('customer_id')})" if old else ""
    summary = f"{action.capitalize()} {entity}{label}" + (f": {json.dumps(body, ensure_ascii=False)}" if body else "")
    return None, {"method": method, "path": f"/{plural}" + (f"/{record_id}" if record_id else ""),
                  "body": body, "summary": summary}


def converse(conversation_id, message):
    """Handle one user message: let the bot call tools, then return its answer or a proposal to confirm."""
    conversation_id, messages = get_conversation(conversation_id)
    if not messages:
        messages.append({"role": "system", "content": SYSTEM})
    messages.append({"role": "user", "content": message})
    proposal, reply, used = None, {}, []
    for _ in range(MAX_ROUNDS):
        reply = chat(messages)
        messages.append(reply)
        calls = reply.get("tool_calls") or []
        if not calls:
            break
        for call in calls:
            name, args = call["function"]["name"], call["function"].get("arguments") or {}
            if name in FORM_FOR and not period_from_user(name, args, messages):
                name = FORM_FOR[name]  # period invented or missing: Python shows the form instead of guessing
            if name in UI_TOOLS:  # a UI tool: the browser shows a form, the user's answer comes back as a message
                ui, question = UI_TOOLS[name]
                messages.append({"role": "tool", "content": "The form is shown to the user. Wait for the answer."})
                messages.append({"role": "assistant", "content": question})
                return {"conversation_id": conversation_id, "reply": question, "ui": [ui], "open": True}
            if name.startswith("get_"):
                data = read(name, args)
                content = json.dumps(data, ensure_ascii=False)
                used.append(f"{name}({', '.join(f'{k}={v}' for k, v in args.items() if v)}) -> "
                            + (f"{len(data)} records" if isinstance(data, list) else data.get("error", "")))
            else:
                error, proposal = propose(name, args)
                content = f"Not possible: {error}" if error else \
                    "Proposal shown to the user. Nothing is saved until the user clicks Yes."
            messages.append({"role": "tool", "content": content})
        if proposal:
            return {"conversation_id": conversation_id, "proposal": proposal}
    text = reply.get("content") or "Sorry, I could not answer that. Please ask in other words."
    sources = "\n\nData read by Python: " + "; ".join(used) if used else "\n\n(No data was read for this answer.)"
    return {"conversation_id": conversation_id, "reply": text + sources}

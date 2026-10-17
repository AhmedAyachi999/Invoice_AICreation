"""One chat for everything: a router bot decides whether a message is a question (-> the assistant with its read
tools) or a change of a customer, product or invoice (-> that bot, bot.converse with its checks). Follow-up answers
stay with the bot that asked."""
import re
import uuid

from chat import assistant, bot
from entities import customers, invoices, products

ROUTER = "inv-router-bot"
BOTS = {"customer": ("inv-customer-bot", customers), "product": ("inv-product-bot", products),
        "invoice": ("inv-invoice-bot", invoices)}
NEGATIVE_PRICE = re.compile(r"-\s*\d")  # "-5", "- 5", "-0.5"
SESSIONS = {}  # conversation_id -> {"last": entity, "waiting": bool, "ids": {entity: bot conversation_id}}


def route(message):
    """Ask the router bot which bot a message belongs to: 'question', 'customer', 'product', 'invoice', or None.
    The bot thinks step by step first; only the word after 'Route:' counts."""
    reply = bot.chat(ROUTER, [{"role": "user", "content": message}]).lower()
    words = [word.strip(".:,") for word in reply.rsplit("route:", 1)[-1].split()]
    return next((word for word in words if word in BOTS or word == "question"), None)  # e.g. "assistant: customer"


def converse(conversation_id, message):
    """Handle one message of the single chat: route it, let that bot answer, return its reply or proposal."""
    if conversation_id not in SESSIONS:
        conversation_id = str(uuid.uuid4())
        SESSIONS[conversation_id] = {"last": None, "waiting": False, "ids": {}}
    session = SESSIONS[conversation_id]
    # Get entity of last session or try to find it
    entity = session["last"] if session["waiting"] else route(message)
    if entity is None:
        return {"conversation_id": conversation_id,
                "reply": "Sorry, I can only help with customers, products and invoices."}
    if entity == "product" and NEGATIVE_PRICE.search(message):  # caught in Python: the bot would refuse or forget it
        new = any(word in message.lower() for word in ("create", "add", "new"))
        return {"conversation_id": conversation_id, "entity": entity,
                "reply": "A price can't be negative. Please enter it in the form.",
                "ui": ["new_product" if new else "edit_product"]}
    if entity == "question":
        result = assistant.converse(session["ids"].get(entity), message)
    else:
        model, module = BOTS[entity]
        result = bot.converse(model, module.check_command, module.build_proposal, module.answer,
                              session["ids"].get(entity), message)
    session["ids"][entity] = result["conversation_id"]
    session["last"] = entity
    session["waiting"] = result.get("open", False)  # a question or an error: the task is not finished yet
    text = result.get("reply", "").lower()
    if entity in ("customer", "product") and result.get("open") and \
            (f"which {entity}" in text or "which one do you mean" in text):
        result["ui"] = [entity]  # "Which customer/product ...?" or several matches: offer a chooser of existing records
    if entity == "product" and result.get("open") and "which product do you want to change" in text:
        result["ui"] = ["edit_product"]  # a price change: product, field and new price in one form
    if entity == "customer" and result.get("open") and \
            ("name of the new customer" in text or "what is the address of" in text):
        result["ui"] = ["new_customer"]  # a new customer: offer the form for name and address
    if entity == "product" and result.get("open") and any(ask in text for ask in
            ["name of the new product", "what is the sell price of"]):
        result["ui"] = ["new_product"]  # a new product: offer the form for name and sell price
    if entity == "invoice" and result.get("open"):  # the invoice bot asks or reports an error: offer pickers
        result["ui"] = [ui for ui, words in [("invoice", ["invoice number", "which invoice"]),
                                             ("status", ["paid or unpaid"]),
                                             ("customer", ["customer"]), ("dates", ["date"]),
                                             ("lines", ["product", "line", "quantity", "item"])]
                        if any(word in text for word in words)]
    return {**result, "conversation_id": conversation_id, "entity": entity}

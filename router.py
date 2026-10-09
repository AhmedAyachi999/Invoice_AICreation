"""One chat for everything: a router bot decides whether a message is a question (-> the assistant with its read
tools) or a change of a customer, product or invoice (-> that bot, bot.converse with its checks). Follow-up answers
stay with the bot that asked."""
import uuid

import assistant
import bot
import customers
import invoices
import products

ROUTER = "inv-router-bot"
BOTS = {"customer": ("inv-customer-bot", customers), "product": ("inv-product-bot", products),
        "invoice": ("inv-invoice-bot", invoices)}
SESSIONS = {}  # conversation_id -> {"last": entity, "waiting": bool, "ids": {entity: bot conversation_id}}


def route(message):
    """Ask the router bot which bot a message belongs to: 'question', 'customer', 'product', 'invoice', or None."""
    words = [word.strip(".:,") for word in bot.chat(ROUTER, [{"role": "user", "content": message}]).lower().split()]
    return next((word for word in words if word in BOTS or word == "question"), None)  # e.g. "assistant: customer"


def converse(conversation_id, message):
    """Handle one message of the single chat: route it, let that bot answer, return its reply or proposal."""
    if conversation_id not in SESSIONS:
        conversation_id = str(uuid.uuid4())
        SESSIONS[conversation_id] = {"last": None, "waiting": False, "ids": {}}
    session = SESSIONS[conversation_id]
    entity = session["last"] if session["waiting"] else route(message)
    if entity is None:
        return {"conversation_id": conversation_id,
                "reply": "Sorry, I can only help with customers, products and invoices."}
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
    if entity in ("customer", "product") and result.get("open") and f"which {entity}" in text:
        result["ui"] = [entity]  # "Which customer/product do you want to ...?": offer a chooser of existing records
    if entity == "invoice" and result.get("open"):  # the invoice bot asks or reports an error: offer pickers
        result["ui"] = [ui for ui, words in [("customer", ["customer"]), ("dates", ["date"]),
                                             ("lines", ["product", "line", "quantity", "item"])]
                        if any(word in text for word in words)]
    return {**result, "conversation_id": conversation_id, "entity": entity}

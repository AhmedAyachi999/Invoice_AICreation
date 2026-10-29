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
NEGATIVE_PRICE = re.compile(r"(?<!\w)-\s*\d")  # "-5", "- 5", "-0.5"; not the dash inside a name like "USB-3"
SESSIONS = {}  # conversation_id -> {"last": entity, "waiting": bool, "ids": {entity: bot conversation_id}}
QUESTIONS = {  # (route, action) -> the bot's own first question; Python asks it when the bot refuses its task
    ("customer", "created"): "What is the name of the new customer?",
    ("customer", "changed"): "Which customer do you want to change?",
    ("customer", "deleted"): "Which customer do you want to delete?",
    ("product", "created"): "What is the name of the new product?",
    ("product", "changed"): "Which product do you want to change?",
    ("product", "deleted"): "Which product do you want to delete?",
    ("invoice", "created"): "What are the invoice date and the due date?",
    ("invoice", "changed"): "Which invoice number?",
    ("invoice", "deleted"): "Which invoice number do you want to delete?",
}


def action(reasoning):
    """The action from the router's line "To do that: a product must be deleted.": 'created', 'changed', 'deleted'
    or None (only read, or no reasoning because the message was a follow-up answer)."""
    line = next((l for l in (reasoning or "").lower().splitlines() if l.startswith("to do that")), "")
    return next((word for word in ("created", "changed", "deleted") if f"must be {word}" in line), None)


def route(message):
    """Ask the router bot which bot a message belongs to: 'question', 'customer', 'product', 'invoice', or None.
    The bot thinks step by step first; only the word after 'Route:' counts.
    The message is sent as "User: <message>", like the examples, so the bot sorts it instead of obeying it.
    Returns (route, reasoning): the reasoning is the bot's text before 'Route:', shown to the user."""
    # "User: " like the examples in the Modelfile: the bot sorts the message instead of reading it as an order
    # about its own text ("remove Tim Wagner" -> "There is no Tim Wagner in the text")
    reply = bot.chat(ROUTER, [{"role": "user", "content": f"User: {message}"}])
    reasoning, _, after = reply.rpartition("Route:")
    words = [word.strip(".:,") for word in (after if reasoning else reply).lower().split()]
    entity = next((word for word in words if word in BOTS or word == "question"), None)  # e.g. "assistant: customer"
    return entity, (reasoning or reply).strip()


def converse(conversation_id, message):
    """Handle one message of the single chat: route it, let that bot answer, return its reply or proposal.
    When the router bot was asked, its reasoning is returned too (shown to the user)."""
    if conversation_id not in SESSIONS:
        conversation_id = str(uuid.uuid4())
        SESSIONS[conversation_id] = {"last": None, "waiting": False, "ids": {}}
    session = SESSIONS[conversation_id]
    # Get entity of last session or try to find it
    entity, reasoning = (session["last"], None) if session["waiting"] else route(message)
    if entity is None:
        return {"conversation_id": conversation_id, "reasoning": reasoning,
                "reply": "Sorry, I can only help with customers, products and invoices."}
    if bot.PYTHON and entity == "product" and NEGATIVE_PRICE.search(message):  # caught in Python: the bot would refuse or forget it
        new = any(word in message.lower() for word in ("create", "add", "new"))
        return {"conversation_id": conversation_id, "entity": entity, "reasoning": reasoning,
                "reply": "A price can't be negative. Please enter it in the form.",
                "ui": ["new_product" if new else "edit_product"]}
    if entity == "question":
        result = assistant.converse(session["ids"].get(entity), message)
    else:
        model, module = BOTS[entity]
        result = bot.converse(model, module.check_command, module.build_proposal, module.answer,
                              session["ids"].get(entity), message)
    question = QUESTIONS.get((entity, action(reasoning)))
    if bot.PYTHON and question and result.get("reply", "").startswith("Sorry, I can only"):  # the bot refused its task
        bot.CONVERSATIONS[result["conversation_id"]][-1]["content"] = question  # the bot's history shows the question
        result = {**result, "reply": question, "open": True}  # the form rules below then offer the matching form
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
    if not bot.PYTHON:
        result.pop("ui", None)  # the bots alone: no forms, the user types the answer to the bot's question
    return {**result, "conversation_id": conversation_id, "entity": entity, "reasoning": reasoning}

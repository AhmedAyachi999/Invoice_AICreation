import functools
import json
import os
import re
import urllib.request
import uuid
from pathlib import Path

LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")  # any OpenAI-compatible server
LLM_MODEL = os.environ.get("LLM_MODEL", "")  # empty: the inv-* bots; set (e.g. llama3.2:3b): that model + the SYSTEM text
LLM_TEMPERATURE = float(os.environ.get("LLM_TEMPERATURE", "0"))
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "120"))  # seconds to wait for one model answer
COMMAND_RE = re.compile(r"\b(CREATE|UPDATE|DELETE|SHOW|REPORT)_(CUSTOMER|PRODUCT|INVOICE|MONTH)\b")
CONVERSATIONS = {}  # conversation_id -> list of messages
PYTHON = os.environ.get("INVOICE_PYTHON", "on") != "off"  # "off" (evaluation only): the bots alone, no Python corrections, no forms
MODELFILES = Path(__file__).parent.parent.parent / "modelfiles"


@functools.cache
def system_prompt(model):
    """The SYSTEM text of a bot, e.g. "inv-customer-bot" -> modelfiles/Modelfile-customer (read once)."""
    text = (MODELFILES / f"Modelfile-{model.split('-')[1]}").read_text(encoding="utf-8")
    return re.search(r'SYSTEM """(.*?)"""', text, re.DOTALL).group(1)


class ModelError(Exception):
    """The language model could not give an answer (not reachable, too slow, or an unexpected answer)."""


def ask_model(path, body):
    """POST body to the model server (LLM_BASE_URL + path) and return the JSON answer; ModelError if that fails."""
    request = urllib.request.Request(f"{LLM_BASE_URL}{path}", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=LLM_TIMEOUT) as response:
            return json.loads(response.read())
    except TimeoutError:
        raise ModelError(f"The language model did not answer within {LLM_TIMEOUT:.0f} seconds. Please try again.")
    except OSError:  # not reachable, refused, or an HTTP error from the server
        raise ModelError("The language model is not reachable. Please check that the model server is running.")
    except ValueError:  # the answer is not JSON
        raise ModelError("The language model gave an unexpected answer. Please try again.")


def chat(model, messages):
    """Send the conversation to the OpenAI-compatible server (LLM_BASE_URL) and return the reply text.
    model is a bot name like "inv-customer-bot" (built with ollama create, its instructions inside).
    With LLM_MODEL set (another server), that model runs instead and Python sends the bot's SYSTEM text first."""
    if LLM_MODEL:  # another server: run LLM_MODEL; for an inv-* bot Python sends its instructions
        if model.startswith("inv-"):
            messages = [{"role": "system", "content": system_prompt(model)}] + messages
        model = LLM_MODEL
    data = ask_model("/chat/completions", {"model": model, "temperature": LLM_TEMPERATURE, "stream": False,
                                           "messages": messages})
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise ModelError("The language model gave an unexpected answer. Please try again.")


def server_ok():
    """True if the model server answers within 3 seconds (for GET /health)."""
    try:
        with urllib.request.urlopen(f"{LLM_BASE_URL}/models", timeout=3):
            return True
    except OSError:  # not reachable, refused or timed out
        return False


def unique_keys(pairs):
    """Build a JSON object, but refuse duplicate keys ({"month": 10, "month": 11} would silently keep only 11)."""
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError(f"duplicate key in {keys}")
    return dict(pairs)


def parse_command(reply):
    """Find a command like 'DELETE_CUSTOMER {"id": "CUS-003"}' in the reply.
    Return ("DELETE_CUSTOMER", {"id": "CUS-003"}), or None if the reply contains no valid command."""
    match = COMMAND_RE.search(reply)
    if not match:
        return None
    try:
        data, _ = json.JSONDecoder(object_pairs_hook=unique_keys).raw_decode(reply[match.end():].lstrip())
    except ValueError:
        return None
    return match.group(0), data


def get_conversation(conversation_id):
    """Return (conversation_id, messages). Unknown or missing id: start a new, empty conversation."""
    if conversation_id not in CONVERSATIONS:
        conversation_id = str(uuid.uuid4())
        CONVERSATIONS[conversation_id] = []
    return conversation_id, CONVERSATIONS[conversation_id]


TARGET_KEYS = ("name", "id")  # the keys that say which record an UPDATE or DELETE changes


def invented_target(command, data, messages):
    """Return the name or number of the record to change if the user never wrote it, else None.
    Stops an UPDATE or DELETE on a record the bot guessed or copied from its examples."""
    if command.startswith("CREATE_"):
        return None
    said = " ".join(m["content"] for m in messages if m["role"] == "user").lower()
    for key in TARGET_KEYS:
        value = str(data.get(key, "")).strip()
        if value and value.lower() not in said:
            return value
    return None


PERIOD_KEYS = ("year", "start", "end")  # parts of a period that the user must have written literally


def invented_period(data, messages):
    """Return the key of a year or date the user never wrote (e.g. 2031 copied from an example), else None."""
    said = " ".join(m["content"] for m in messages if m["role"] == "user").lower()
    for key in PERIOD_KEYS:
        value = str(data.get(key, "")).strip().lower()
        if value and value not in said:
            return key
    return None


def clean_command(data):
    """Empty the values the bot filled in by itself: null and placeholders that repeat their key ("year": "year").
    The checks then treat them as missing."""
    cleaned = {}
    for key, value in data.items():
        text = "" if value is None else str(value).strip().lower()
        cleaned[key] = "" if not text or text == key.lower() else value
    return cleaned


def chosen_delete(messages, message):
    """The DELETE command when the chooser answers "Which customer/product/invoice ... delete?", else None.
    The action comes from the question and the record from the chooser, so the bot is not asked."""
    last = next((m["content"] for m in reversed(messages) if m["role"] == "assistant"), "")
    match = re.search(r"which (customer|product|invoice)\b.*\bdelete\b", last.lower())
    if not match:
        return None
    entity, text = match.group(1), message.strip()
    if entity == "invoice":  # the invoice chooser sends only the number, e.g. "INV-004"
        return ("DELETE_INVOICE", {"id": text.upper()}) if re.fullmatch(r"INV-\d+", text, re.I) else None
    prefix = f"{entity}: "  # the customer and product choosers send "customer: Tim Wagner"
    return (f"DELETE_{entity.upper()}", {"name": text[len(prefix):].strip()}) \
        if text.lower().startswith(prefix) else None


def converse(model, check_command, build_proposal, answer, conversation_id, message):
    """Handle one user message: ask the bot, check its command, return its reply, Python's message or a proposal.
    With PYTHON off (evaluation only) the bot's command is used without Python's corrections and checks."""
    conversation_id, messages = get_conversation(conversation_id)
    messages.append({"role": "user", "content": message})
    command = chosen_delete(messages, message) if PYTHON else None  # the chooser answered a delete question
    reply = f"{command[0]} {json.dumps(command[1], ensure_ascii=False)}" if command else chat(model, messages)
    command = command or parse_command(reply)
    if PYTHON and command is None and COMMAND_RE.search(reply):
        reply = "Sorry, I didn't understand that. Please say it again in other words."
    # "open": the task is not finished (a question or an error), so the user's next message belongs to this bot
    if command is None:
        messages.append({"role": "assistant", "content": reply})
        return {"conversation_id": conversation_id, "reply": reply, "open": not reply.startswith("Sorry, I can only")}
    if PYTHON:
        command = (command[0], clean_command(command[1]))
        if invented_target(*command, messages):
            entity = command[0].split("_")[1].lower()
            question = f"Which {entity} do you mean? Please write its {'number' if entity == 'invoice' else 'name'}."
            messages.append({"role": "assistant", "content": question})
            return {"conversation_id": conversation_id, "reply": question, "open": True}
        if invented_period(command[1], messages):
            question = "Which year do you mean?" if invented_period(command[1], messages) == "year" else "Which date do you mean?"
            messages.append({"role": "assistant", "content": question})
            return {"conversation_id": conversation_id, "reply": question, "open": True}
        error = check_command(*command)
        if error:
            # Python's message goes straight to the user; the bot sees it in the conversation as what was said
            messages.append({"role": "assistant", "content": error})
            return {"conversation_id": conversation_id, "reply": error, "open": True}
    if command[0].startswith(("SHOW_", "REPORT_")):
        text = answer(*command)
        messages.append({"role": "assistant", "content": text})
        return {"conversation_id": conversation_id, "reply": text}
    messages.append({"role": "assistant", "content": reply})
    return {"conversation_id": conversation_id, "proposal": build_proposal(*command)}

import json
import re
import urllib.request
import uuid

OLLAMA_URL = "http://localhost:11434/api/chat"
COMMAND_RE = re.compile(r"\b(CREATE|UPDATE|DELETE|SHOW|REPORT)_(CUSTOMER|PRODUCT|INVOICE|MONTH)\b")
CONVERSATIONS = {}  # conversation_id -> list of messages


def chat(model, messages):
    """Send the conversation to an Ollama model and return its reply text (temperature 0, like all our bots)."""
    body = json.dumps({"model": model, "messages": messages, "stream": False,
                       "options": {"temperature": 0}}).encode()
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())["message"]["content"]


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


def converse(model, check_command, build_proposal, answer, conversation_id, message):
    """Handle one user message: ask the bot, check its command, return its reply, Python's message or a proposal."""
    conversation_id, messages = get_conversation(conversation_id)
    messages.append({"role": "user", "content": message})
    reply = chat(model, messages)
    command = parse_command(reply)
    if command is None and COMMAND_RE.search(reply):
        reply = "Sorry, I didn't understand that. Please say it again in other words."
    # "open": the task is not finished (a question or an error), so the user's next message belongs to this bot
    if command is None:
        messages.append({"role": "assistant", "content": reply})
        return {"conversation_id": conversation_id, "reply": reply, "open": not reply.startswith("Sorry, I can only")}
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

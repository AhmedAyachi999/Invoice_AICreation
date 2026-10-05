import json
import re
import urllib.request
import uuid

OLLAMA_URL = "http://localhost:11434/api/chat"
COMMAND_RE = re.compile(r"\b(CREATE|UPDATE|DELETE)_(CUSTOMER|PRODUCT|INVOICE)\b")
CONVERSATIONS = {}  # conversation_id -> list of messages


def chat(model, messages):
    """Send the conversation to an Ollama model and return its reply text."""
    body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())["message"]["content"]


def parse_command(reply):
    """Find a command like 'DELETE_CUSTOMER {"id": "CUS-003"}' in the reply.
    Return ("DELETE_CUSTOMER", {"id": "CUS-003"}), or None if the reply contains no valid command."""
    match = COMMAND_RE.search(reply)
    if not match:
        return None
    try:
        data, _ = json.JSONDecoder().raw_decode(reply[match.end():].lstrip())
    except json.JSONDecodeError:
        return None
    return match.group(0), data


def get_conversation(conversation_id):
    """Return (conversation_id, messages). Unknown or missing id: start a new, empty conversation."""
    if conversation_id not in CONVERSATIONS:
        conversation_id = str(uuid.uuid4())
        CONVERSATIONS[conversation_id] = []
    return conversation_id, CONVERSATIONS[conversation_id]


def converse(model, check_command, build_proposal, conversation_id, message):
    """Handle one user message: ask the bot, check its command, return its reply, Python's message or a proposal."""
    conversation_id, messages = get_conversation(conversation_id)
    messages.append({"role": "user", "content": message})
    reply = chat(model, messages)
    command = parse_command(reply)
    if command is None:
        messages.append({"role": "assistant", "content": reply})
        return {"conversation_id": conversation_id, "reply": reply}
    error = check_command(*command)
    if error:
        # Python's message goes straight to the user; the bot sees it in the conversation as what was said
        messages.append({"role": "assistant", "content": error})
        return {"conversation_id": conversation_id, "reply": error}
    messages.append({"role": "assistant", "content": reply})
    return {"conversation_id": conversation_id, "proposal": build_proposal(*command)}

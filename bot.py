import json
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"


def chat(model, messages):
    """Send the conversation to an Ollama model and return its reply text."""
    body = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    request = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())["message"]["content"]

"""Help with using the software (RAG): the user guide docs/user_guide.md is cut into sections, the sections that
match a question are found by meaning (embeddings) and given to the bot as the only source for its answer."""
import json
import math
import pathlib
import re
import urllib.request

from chat.bot import OLLAMA_URL, chat

GUIDE = pathlib.Path(__file__).parent.parent.parent / "docs" / "user_guide.md"
EMBED_MODEL = "nomic-embed-text"  # local embedding model (ollama pull nomic-embed-text)
EMBED_URL = OLLAMA_URL.replace("/api/chat", "/api/embed")
SECTIONS = []  # the sections with their vectors, filled on the first help question
MODEL = "llama3.2:3b"
SYSTEM = ("You answer questions about how to use the AI Invoice Assistant, a small invoicing program. "
          "With each question you get a few sections of the user guide.\n"
          "Rules:\n"
          "- Answer only with what these sections say. Never invent buttons, forms, commands or rules.\n"
          "- Words with the same meaning count as the same: a bill is an invoice, remove means delete, client means "
          "customer, item means product, revenue or sales mean turnover.\n"
          "- If the user asks about something the sections do not describe (for example exporting, printing, e-mail or "
          "anything else that is not in the sections), it does not exist in the program: reply exactly: "
          "\"I cannot help with that.\"\n"
          "- Answer in 1 to 3 short sentences in plain English: tell the user what to type or click.\n"
          "- Do not mention the sections or the user guide in your answer.")


def load_sections():
    """Cut the user guide into sections at each '## ' heading: [{"title", "text"}].
    The comment and the '# ' title at the top are not a section."""
    text = re.sub(r"<!--.*?-->", "", GUIDE.read_text(encoding="utf-8"), flags=re.S)  # drop the comment for authors
    sections = []
    for part in re.split(r"^## ", text, flags=re.M)[1:]:  # [0] is everything before the first section
        title, _, body = part.partition("\n")
        sections.append({"title": title.strip(), "text": body.strip()})
    return sections


def embed(texts):
    """Turn texts into vectors (768 numbers each) with the local embedding model: similar meaning, similar numbers."""
    body = json.dumps({"model": EMBED_MODEL, "input": texts}).encode()
    request = urllib.request.Request(EMBED_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())["embeddings"]


def build_index():
    """Embed all sections once (on the first help question) and keep them in memory with their vectors.
    After changing the user guide, restart the server."""
    if not SECTIONS:
        sections = load_sections()
        vectors = embed([f"search_document: {s['title']}\n{s['text']}" for s in sections])
        SECTIONS.extend({**s, "vector": v} for s, v in zip(sections, vectors))
    return SECTIONS


def search(question, k=3):
    """The k sections whose meaning is closest to the question, best first: [(score, section)].
    Score = cosine similarity of the vectors: near 1 = same meaning, lower = less related."""
    asked = embed([f"search_query: {question}"])[0]

    def cosine(vector):
        dot = sum(x * y for x, y in zip(asked, vector))
        return dot / (math.sqrt(sum(x * x for x in asked)) * math.sqrt(sum(y * y for y in vector)))

    return sorted(((cosine(s["vector"]), s) for s in build_index()), key=lambda pair: -pair[0])[:k]


def answer(question):
    """Answer a question about using the software from the 3 best matching sections of the user guide only.
    Python adds which sections were used, so the user can check the answer."""
    found = search(question)
    sources = "\n\n".join(f"## {s['title']}\n{s['text']}" for _, s in found)
    reply = chat(MODEL, [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": f"{sources}\n\nQuestion: {question}"}])
    return reply.strip() + "\n\nFrom the user guide: " + " · ".join(s["title"] for _, s in found)

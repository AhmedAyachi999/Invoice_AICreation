# Project overview

AI Invoice Assistant: a local REST API (FastAPI, 127.0.0.1) for customers, products and invoices, with Ollama bots
(llama3.2:3b, temperature 0). The specification is in `docs/`: requirements.pdf, architecture.pdf, model_choice.pdf.

# How we write code together

- One function at a time. Never a whole file, class or several functions at once.
- For each function:
  0. Say in which file (module/class) we are working right now, e.g. "File: storage.py".
  1. Say in 1-2 sentences why it is needed (which requirement or decision it serves).
  2. Show the exact code in the chat.
  3. Wait for approval. Only then write it to the file.
- The same applies to test scripts.
- Keep explanations short.
- Commands that don't write code (installs, running tests, ollama commands) can run without asking.

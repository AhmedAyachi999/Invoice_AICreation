"""Hangs and environment: 14 (bot, 5 runs; run this file last, it also reads the timings of the other files)
and 27 (Ollama not reachable, 1 run)."""
import helpers  # first: points the database to a temporary copy
from chat import assistant, bot

LIMIT = 120  # seconds per reply


def scenario_14(run):
    """"what is the address of Mara Quist?" (doesn't exist): a reply within 120 s."""
    run.check("precondition: Mara Quist doesn't exist", all(c["name"] != "Mara Quist" for c in helpers.get("/customers")))
    data = run.say("what is the address of Mara Quist?")
    run.useful(data)
    seconds = float(helpers.TIMINGS.read_text(encoding="utf-8").splitlines()[-1].split("\t")[0])
    run.check(f"reply within {LIMIT} s ({seconds:.1f} s)", seconds <= LIMIT)
    return run.done()


def all_messages(run):
    """Every message of the other scenarios (timings.txt): each within 120 s; print the slowest."""
    rows = [line.split("\t", 2) for line in helpers.TIMINGS.read_text(encoding="utf-8").splitlines()]
    slowest = max(rows, key=lambda row: float(row[0]))
    run.out(f"    {len(rows)} messages, slowest {slowest[0]} s (scenario {slowest[1]}): {slowest[2]!r}")
    run.check(f"all {len(rows)} replies within {LIMIT} s", all(float(row[0]) <= LIMIT for row in rows))
    return run.done(f"slowest {slowest[0]} s, scenario {slowest[1]}")


def scenario_27(run):
    """Ollama not reachable: a clear error reply or HTTP 5xx with a message; no crash; database unchanged."""
    before = helpers.snapshot()
    closed = "http://127.0.0.1:9/api/chat"  # a closed port, only in this test
    bot.OLLAMA_URL, assistant.OLLAMA_URL = closed, closed
    try:
        response = helpers.client.post("/chat", json={"message": "list my customers", "conversation_id": None})
        run.out(f">>> list my customers\n    HTTP {response.status_code}: {response.text!r}")
        run.check("no crash of the test client", True)
        text = response.json().get("reply", "") if response.status_code == 200 else response.text
        run.check("a clear error reply or HTTP 5xx with a message",
                  (response.status_code == 200 and text.strip()) or
                  (response.status_code >= 500 and text.strip() and text.strip() != "Internal Server Error"))
    except Exception as error:  # the test client crashed
        run.check(f"no crash of the test client ({error!r})", False)
    finally:
        bot.OLLAMA_URL, assistant.OLLAMA_URL = "http://localhost:11434/api/chat", "http://localhost:11434/api/chat"
    run.check("database unchanged", helpers.snapshot() == before)
    return run.done()


if __name__ == "__main__":
    helpers.repeat("14", scenario_14, 5)
    helpers.repeat("14-all", all_messages, 1)
    helpers.repeat("27", scenario_27, 1)

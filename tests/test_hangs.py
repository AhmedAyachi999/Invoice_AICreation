"""Hangs and environment: 14 (bot, 5 runs; run this file last, it also reads the timings of the other files)
and 27 (model server not reachable, 1 run)."""
import time

import helpers  # first: points the database to a temporary copy
from chat import bot  # noqa: E402

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
    """Model server not reachable: a fast HTTP 503 with a clear message (no hang, no 500); database unchanged."""
    before = helpers.snapshot()
    old_url = bot.LLM_BASE_URL
    bot.LLM_BASE_URL = "http://127.0.0.1:9/v1"  # a closed port, only in this test; every model call reads it
    expected = "The language model is not reachable. Please check that the model server is running."
    try:
        started = time.time()
        response = helpers.client.post("/chat", json={"message": "list my customers", "conversation_id": None})
        seconds = time.time() - started
        run.out(f">>> list my customers\n    HTTP {response.status_code}, {seconds:.1f} s: {response.text!r}")
        run.check("no crash of the test client", True)
        run.check(f"answer within {LIMIT} s ({seconds:.1f} s)", seconds <= LIMIT)
        run.check("HTTP 503 (not 500)", response.status_code == 503)
        detail = response.json().get("detail") if response.headers.get("content-type", "").startswith(
            "application/json") else None
        run.check(f"detail = {expected!r}", detail == expected)
    except Exception as error:  # the test client crashed
        run.check(f"no crash of the test client ({error!r})", False)
    finally:
        bot.LLM_BASE_URL = old_url
    run.check("database unchanged", helpers.snapshot() == before)
    return run.done()


if __name__ == "__main__":
    helpers.repeat("14", scenario_14, 5)
    helpers.repeat("14-all", all_messages, 1)
    helpers.repeat("27", scenario_27, 1)

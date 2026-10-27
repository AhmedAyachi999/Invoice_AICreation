"""Shared helpers for the chat tests: a temporary database from seed/demo_data.json, the TestClient and the steps
(chat message, form, Yes, database snapshot, checks). Run the tests with PYTHONPATH=app."""
import json
import re
import sys
import tempfile
import time
from datetime import date, timedelta
from pathlib import Path

from core import storage  # only sets paths, opens no database

ROOT = Path(__file__).parent.parent
TMP = Path(tempfile.gettempdir()) / "invoice_tests"
TMP.mkdir(exist_ok=True)
storage.DB_PATH = TMP / "start.db"  # never the real database, also not during the imports below
storage.DB_PATH.unlink(missing_ok=True)  # seed() fills only a database that doesn't exist yet
storage.seed()  # built from seed/demo_data.json (data/ is not in git)

from fastapi.testclient import TestClient  # noqa: E402
import api  # noqa: E402
from chat import assistant  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
client = TestClient(api.app, raise_server_exceptions=False)  # a server error comes back as HTTP 500, like in the browser
TIMINGS = TMP / "timings.txt"  # seconds per /chat message, read by test_hangs.py (scenario 14)
RESULTS = TMP / "results.jsonl"  # one line per run, used to write the results file
TODAY = date.today()


def day(offset=0):
    """A date as DD/MM/YYYY, offset days from today (the date picker allows no past invoice date)."""
    return (TODAY + timedelta(days=offset)).strftime("%d/%m/%Y")


def fresh_db():
    """A new database from seed/demo_data.json for one run; storage uses it from now on."""
    storage.DB_PATH = Path(tempfile.mkdtemp(dir=TMP)) / "invoices.db"  # a new folder: the file doesn't exist yet
    storage.seed()


def get(path):
    """GET a record or list; None if it doesn't exist (404)."""
    response = client.get(path)
    return response.json() if response.status_code == 200 else None


def snapshot():
    """All customers, products and invoices, to compare before and after."""
    return {kind: get(f"/{kind}") for kind in ("customers", "products", "invoices")}


def example_names():
    """Names used in the bots' examples (modelfiles/ and assistant.SYSTEM) that are not in the database."""
    text = "".join(p.read_text(encoding="utf-8") for p in (ROOT / "modelfiles").glob("Modelfile-*")) + assistant.SYSTEM
    names = set(re.findall(r'"(?:name|customer|product)":\s*"([^"]+)"', text))
    real = {r["name"] for kind in ("customers", "products") for r in get(f"/{kind}")}
    return sorted(names - real)


class Run:
    """One run of a scenario: its own database copy, conversation, printed exchange and checks."""

    def __init__(self, scenario, number):
        fresh_db()
        self.scenario, self.cid, self.ok, self.log = scenario, None, True, []
        self.out(f"\n===== Scenario {scenario}, run {number} =====")

    def out(self, text):
        """Print a line and keep it for the results file."""
        print(text)
        self.log.append(text)

    def say(self, message, cid="own"):
        """Send a chat message like the website (POST /chat) and print the raw exchange."""
        started = time.time()
        response = client.post("/chat", json={"message": message,
                                              "conversation_id": self.cid if cid == "own" else cid})
        seconds = time.time() - started
        with open(TIMINGS, "a", encoding="utf-8") as file:
            file.write(f"{seconds:.1f}\t{self.scenario}\t{message}\n")
        data = response.json() if response.headers.get("content-type", "").startswith("application/json") \
            else {"reply": response.text}
        if cid == "own":
            self.cid = data.get("conversation_id", self.cid)
        self.out(f">>> {message}\n    HTTP {response.status_code}, {seconds:.1f} s, entity={data.get('entity')}\n"
                 f"    reply: {data.get('reply')!r}\n    ui: {data.get('ui')}\n    proposal: {data.get('proposal')}")
        return data

    def follow(self, data, fill, steps=8):
        """Fill the forms that open (fill: ui name -> the message app.js sends) until a proposal or no form."""
        replies = [data]
        for _ in range(steps):
            form = next((ui for ui in data.get("ui") or [] if ui in fill), None)
            if data.get("proposal") or form is None:
                break
            data = self.say(fill[form])
            replies.append(data)
        return data, replies

    def yes(self, proposal):
        """The user clicks Yes: send proposal.body with proposal.method to proposal.path (confirmProposal)."""
        response = client.request(proposal["method"], proposal["path"], json=proposal["body"]) \
            if proposal["body"] is not None else client.request(proposal["method"], proposal["path"])
        self.out(f">>> Yes: {proposal['method']} {proposal['path']}\n    HTTP {response.status_code}: {response.text}")
        return response

    def check(self, name, passed):
        """One PASS/FAIL line."""
        self.ok = self.ok and bool(passed)
        self.out(f"{'PASS' if passed else 'FAIL'}: {name}")
        return passed

    def useful(self, data):
        """The agreed rule: an empty reply or "Sorry, I can only help ..." is a FAIL."""
        text = (data.get("reply") or "").strip()
        return self.check("reply is useful", data.get("proposal") or (text and not text.startswith("Sorry, I can only")))

    def done(self, observed=None):
        """Store the run's result (observed = text for undecided scenarios)."""
        with open(RESULTS, "a", encoding="utf-8") as file:
            file.write(json.dumps({"scenario": self.scenario, "ok": self.ok, "observed": observed,
                                   "log": "\n".join(self.log)}, ensure_ascii=False) + "\n")
        return self.ok


def repeat(scenario, function, runs):
    """Run a scenario function runs times, each with a new Run; print passes/runs."""
    passes = sum(bool(function(Run(scenario, number))) for number in range(1, runs + 1))
    print(f"\n##### Scenario {scenario}: {passes}/{runs} passed")
    return passes

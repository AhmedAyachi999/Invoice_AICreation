"""Run a customer bot WITHOUT the judge. Usage: python bot_only.py <model> G|N   (G = general tests, N = hold-out)"""
import sys
from pathlib import Path

model, which = sys.argv[1], sys.argv[2]
here = Path(__file__).parent
if which == "G":
    exec((here / "general_tests.py").read_text(encoding="utf-8").split("for tid, message, expected in TESTS:")[0])
    cases = TESTS
else:
    exec((here / "new_scenarios.py").read_text(encoding="utf-8").split("for sid, message, expected in SCENARIOS:")[0])
    cases = SCENARIOS

score = 0
for cid, message, expected in cases:
    answer = bot.chat(model, [{"role": "user", "content": message}]).strip()
    ok = is_correct(answer, expected)
    score += ok
    print("\t".join([cid, message, answer.replace("\n", " | "), "correct" if ok else "wrong"]))
print(f"SCORE\t{score}/{len(cases)}")

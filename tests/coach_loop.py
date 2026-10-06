"""Bot answers -> coach checks -> if not OK, bot answers again -> coach checks again ... until OK (max 3 rounds)."""
import re
from pathlib import Path

source = Path(__file__).with_name("new_scenarios.py").read_text(encoding="utf-8")
exec(source.split("for sid, message, expected in SCENARIOS:")[0])  # SCENARIOS, is_correct, describe, bot

MAX_ROUNDS = 3


def coach(message, answer):
    text = bot.chat("inv-judge-bot",[{"role": "user", "content": f"User message: {message}\nAssistant answer: {answer}"}])
    m = re.search(r"Message to the assistant:\s*(.*)", text, re.S)
    return (m.group(1) if m else text).strip().replace("\n", " ")


for sid, message, expected in SCENARIOS:
    history = [{"role": "user", "content": message}]
    answer = bot.chat("inv-customer-bot", history).strip()
    first = answer
    steps = []
    for _ in range(MAX_ROUNDS):
        feedback = coach(message, answer)
        steps.append(feedback)
        if feedback.upper().startswith("OK") or feedback.upper().startswith("MESSAGE TO THE ASSISTANT: OK"):
            break
        history += [{"role": "assistant", "content": answer},
                    {"role": "user", "content": f"Correction from the checker: {feedback} Give your corrected answer to my previous message."}]
        answer = bot.chat("inv-customer-bot", history).strip()
        steps.append("-> " + answer.replace("\n", " | "))
    rounds = sum(1 for s in steps if s.startswith("-> "))
    print("\t".join([sid, message, first.replace("\n", " | "), "correct" if is_correct(first, expected) else "wrong",
                     " || ".join(steps), str(rounds), "correct" if is_correct(answer, expected) else "wrong"]))

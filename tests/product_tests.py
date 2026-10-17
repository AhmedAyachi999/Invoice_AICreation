"""20 single-message scenarios for the product bot (bot alone). Usage: python product_tests.py [model]"""
import sys

from chat import bot

# (id, user message, expected)
#   ("cmd", KEYWORD, {field: expected})  names/fields exact (lower case), prices compared as numbers
#   ("ask", [words, one must appear])    -> a question, no command
#   ("sorry",)                           -> the Sorry sentence, no command
TESTS = [
    ("P1", "I want to add a product", ("ask", ["name"])),
    ("P2", "new product: Office Chair Atlas", ("ask", ["price"])),
    ("P3", "add Office Chair Atlas, sell price 189, buy price 120",
     ("cmd", "CREATE_PRODUCT", {"name": "office chair atlas", "sell_price": 189, "buy_price": 120})),
    ("P4", "please create the product USB Cable 2m, we sell it for 7,50 EUR and buy it for 2,20 EUR",
     ("cmd", "CREATE_PRODUCT", {"name": "usb cable 2m", "sell_price": 7.5, "buy_price": 2.2})),
    ("P5", "add Printer Paper A4 with a sell price of 4.99", ("ask", ["buy"])),
    ("P6", "delete a product", ("ask", ["which"])),
    ("P7", "delete Monitor Stand Basic", ("cmd", "DELETE_PRODUCT", {"name": "monitor stand basic"})),
    ("P8", "we don't sell the Webcam HD anymore", ("cmd", "DELETE_PRODUCT", {"name": "webcam hd"})),
    ("P9", "I need to change a product", ("ask", ["which"])),
    ("P10", "change the sell price of Webcam HD", ("ask", ["price"])),
    ("P11", "Webcam HD now sells for 59",
     ("cmd", "UPDATE_PRODUCT", {"name": "webcam hd", "field": "sell_price", "value": 59})),
    ("P12", "the buy price of Office Chair Atlas went up to 130",
     ("cmd", "UPDATE_PRODUCT", {"name": "office chair atlas", "field": "buy_price", "value": 130})),
    ("P13", "rename USB Cable 2m to USB-C Cable 2m",
     ("cmd", "UPDATE_PRODUCT", {"name": "usb cable 2m", "field": "name", "value": "usb-c cable 2m"})),
    ("P14", "Printer Paper A4 should be called Copy Paper A4",
     ("cmd", "UPDATE_PRODUCT", {"name": "printer paper a4", "field": "name", "value": "copy paper a4"})),
    ("P15", "rename a product", ("ask", ["which", "name"])),
    ("P16", "what is the capital of Spain?", ("sorry",)),
    ("P17", "give me a recipe for pancakes", ("sorry",)),
    ("P18", "add a customer called Jana Pohl", ("sorry",)),
    ("P19", "add", ("ask", ["name", "what", "which"])),
    ("P20", "remove the product", ("ask", ["which"])),
]
EXACT = {"name", "field"}
NUMBERS = {"sell_price", "buy_price"}


def same_number(got, expected):
    try:
        return abs(float(str(got).replace(",", ".")) - expected) < 0.001
    except ValueError:
        return False


def is_correct(answer, expected):
    command = bot.parse_command(answer)
    if expected[0] == "cmd":
        if command is None or command[0] != expected[1]:
            return False
        for key, want in expected[2].items():
            got = command[1].get(key, "")
            if isinstance(want, (int, float)):
                if not same_number(got, want):
                    return False
            elif str(got).strip().lower() != want:
                return False
        return True
    if command is not None:
        return False
    if expected[0] == "sorry":
        return "only help with products" in answer.lower()
    return "?" in answer and any(w in answer.lower() for w in expected[1])


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "inv-product-bot"
    score = 0
    for tid, message, expected in TESTS:
        answer = bot.chat(model, [{"role": "user", "content": message}]).strip()
        ok = is_correct(answer, expected)
        score += ok
        print("\t".join([tid, message, answer.replace("\n", " | "), "correct" if ok else "wrong"]))
    print(f"SCORE\t{score}/{len(TESTS)}")

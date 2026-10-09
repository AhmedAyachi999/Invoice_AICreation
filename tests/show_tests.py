"""SHOW cases (single messages through bot.converse): the bot writes SHOW_..., Python answers from the database.
Each case lists texts that must all appear in the final answer, or NO_SHOW: the bot must not write a SHOW command.
Usage: python tests/show_tests.py"""
import bot
import reports

NO_SHOW = None
CASES = {
    "inv-report-bot": (reports, [
        ("SC1", "where does Lena Müller live?", ["Lena Müller"]),
        ("SC2", "what is the address of Tim Wagner?", ["Feldstr. 14, 44135 Dortmund"]),
        ("SC3", "show me the customer Sofia Rossi", ["Kirchplatz 6, 90402 Nürnberg"]),
        ("SC4", "do we have a customer called Omar Haddad?", ["Mühlenweg 8, 30159 Hannover"]),
        ("SC5", "show me the customers called Müller", ["Jonas Müller", "Lena Müller", "Paul Müller-Lang"]),
        ("SC6", "where does Hartmann live?", ["Felix Hartmann"]),
        ("SC7", "where does Ingo Walther live?", ["There is no customer called Ingo Walther"]),
        ("SC8", "show me the customer", NO_SHOW),
        ("SC9", "Lena Müller moved to Domstr. 1, 50668 Köln", NO_SHOW),
        ("SC10", "delete Karl Becker", NO_SHOW),
        ("SP1", "what does the Office Chair Comfort cost?", ["249"]),
        ("SP2", "what is the buy price of Monitor 27?", ["160"]),
        ("SP3", "show me the Desk Lamp", ["Desk Lamp Pro"]),
        ("SI1", "is INV-004 paid?", ["INV-004", "unpaid"]),
        ("SI2", "what is the total of INV-006?", ["956.00"]),
        ("SI3", "show me invoice INV-099", ["There is no invoice INV-099"]),
    ]),
}

real_chat = bot.chat
raw = []
bot.chat = lambda model, messages: raw.append(real_chat(model, messages)) or raw[-1]  # remember the bot's raw reply

for model, (module, cases) in CASES.items():
    score = 0
    for case_id, message, expected in cases:
        result = bot.converse(model, module.check_command, None, module.answer, None, message)
        answer = result.get("reply") or "PROPOSAL: " + result["proposal"]["summary"]
        command = bot.parse_command(raw[-1])
        if expected is NO_SHOW:
            ok = command is None or not command[0].startswith("SHOW_")
        else:
            ok = all(text in answer for text in expected)
        score += ok
        print(f"{case_id}\t{message}\n\tbot:    {raw[-1]}\n\tanswer: {answer}\n\t{'OK' if ok else 'WRONG'}")
    print(f"SCORE {model}\t{score}/{len(cases)}")

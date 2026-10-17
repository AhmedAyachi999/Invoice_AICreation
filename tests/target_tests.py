"""Five messages that name no record. The bot may guess one; Python must ask instead (bot.invented_target).
Usage: python tests/target_tests.py"""
from chat import bot
from entities import customers, invoices

CASES = [
    ("T1", "inv-customer-bot", customers, "delete the customer"),
    ("T2", "inv-customer-bot", customers, "remove one of our customers please"),
    ("T3", "inv-customer-bot", customers, "update the address of the customer"),
    ("T4", "inv-invoice-bot", invoices, "mark an invoice as paid"),
    ("T5", "inv-invoice-bot", invoices, "change the due date of the invoice to 30/11/2026"),
]

real_chat = bot.chat
raw = {}
bot.chat = lambda model, messages: raw.setdefault(len(raw), real_chat(model, messages))  # remember the bot's raw reply

for case_id, model, module, message in CASES:
    result = bot.converse(model, module.check_command, module.build_proposal, module.answer, None, message)
    answer = result.get("reply") or "PROPOSAL: " + result["proposal"]["summary"]
    print(f"{case_id}\t{message}\n\tbot:    {raw[len(raw) - 1]}\n\tanswer: {answer}\n\t"
          f"{'WRONG' if 'proposal' in result else 'OK'}")

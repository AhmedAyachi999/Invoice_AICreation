# AI Invoice Assistant – Problem statement and core scenarios

## Problem statement

A small company has to manage its customers, products and invoices, and it needs to know its turnover per
customer, per product and per month. Doing this by hand in spreadsheets is slow and error-prone: wrong totals,
duplicate invoice numbers, and reports that have to be added up manually.

**The service in one sentence:** the AI Invoice Assistant manages customers, products and invoices through a chat
in plain English and calculates the turnover, with a local language model that understands the user and Python
that checks, calculates and saves.

**Who uses it:** one person in the company, on their own computer (no login, no network access).

**Division of work:**

| The AI (llama3.2:3b, local, through Ollama) | Python |
|---|---|
| understands what the user wants (router, change bots, assistant) | looks records up, checks every rule, calculates all numbers |
| asks for missing information, opens the right form | assigns the numbers (CUS-001, PRD-001, INV-001) |
| answers questions from the data Python gives it | writes lists and turnover answers itself |
| proposes a change | saves – only after the user's Yes, and only after checking again |

## Core scenarios

All four run on the example data (`seed/demo_data.json`) through the website's single chat (`POST /chat`).

### S1 – Create an invoice

| | |
|---|---|
| **Goal** | Write an invoice for an existing customer. |
| **Precondition** | Customer Karl Becker (CUS-008) and product Desk Lamp (PRD-001, 29.90) exist. |

| Step | The user | The program |
|---|---|---|
| 1 | types "new invoice for Karl Becker" | invoice bot: "What are the invoice date and the due date?" + **date picker** (no date in the past, due date not before the invoice date) |
| 2 | picks 30/10/2026 and 30/11/2026 | "Which products and quantities?" + **product lines picker** |
| 3 | adds 2 × Desk Lamp | "Who is the customer?" + **customer list** (the bot asks again although the name was given – known limitation) |
| 4 | picks Karl Becker | "Is the invoice paid or unpaid?" + **Paid / Unpaid** |
| 5 | clicks Unpaid | Python looks up the names in the database and replaces them by the record numbers (Karl Becker → CUS-008, Desk Lamp → PRD-001), takes the product's price and shows the summary with **Yes / No**: *Create invoice for CUS-008 (Karl Becker) \| date 30/10/2026 \| due 30/11/2026 \| unpaid \| 1: 2 x Desk Lamp x 29.90 = 59.80 \| total 59.80* |
| 6 | clicks **Yes** | `POST /invoices` checks everything again and saves: "Saved as INV-015." The invoices table is refreshed. |

**Result:** INV-015 is stored in the database with its line and the price of the day (29.90). Nothing was saved
before the Yes.

### S2 – A change that Python refuses

| | |
|---|---|
| **Goal** | Delete a customer – who still has invoices. |
| **Precondition** | Karl Becker is used in invoices. |

| Step | The user | The program |
|---|---|---|
| 1 | types "delete the customer Karl Becker" | customer bot: "Which customer do you want to delete?" + **customer list** |
| 2 | picks Karl Becker | Python checks the rule *a customer with invoices cannot be deleted*: "Karl Becker cannot be deleted: used in invoices INV-007, INV-011, INV-015." |

**Result:** no Yes/No question is shown and nothing is deleted. The rule is checked by Python, not by the AI, and
the delete endpoint checks it again (`DELETE /customers/…` → 400).

### S3 – Turnover per customer

| | |
|---|---|
| **Goal** | See how much each customer brought in during a year. |
| **Precondition** | Paid invoices exist in 2026. |

| Step | The user | The program |
|---|---|---|
| 1 | types "turnover per customer" | the router sends it to the assistant, which opens the **turnover form**: "Please choose the period and, if you want, one customer." |
| 2 | picks 01/01/2026 – 31/12/2026, all customers | Python answers without the AI: *from 01/01/2026 to 31/12/2026: Karl Becker 3065.00, Lena Müller 113.90, Felix Hartmann 92.30, total 3271.20.* |

**Result:** the numbers come from `reports.py` – only **paid** invoices, counted by their **due date**. The same
report is available without AI at `GET /reports/customers?start=01/01/2026&end=31/12/2026`.

### S4 – A question about the data

| | |
|---|---|
| **Goal** | Find out which invoices are still open. |

| Step | The user | The program |
|---|---|---|
| 1 | types "which invoices are unpaid?" | the router sends it to the assistant; it calls its tool `show_invoices(status="unpaid")` and Python writes the list: one line per invoice (number, customer, dates, status, total) and *10 unpaid invoices.* |

**Result:** the list and the count come from the database, not from the AI. For free questions where the AI
writes the answer itself (e.g. "which customers live in Dortmund?"), the answer ends with the data Python read
("Data read by Python: get_customers() -> 17 records"), so the user can check it.

## What the scenarios show

- **The AI understands, Python decides.** In every scenario the AI only sorts the message, asks or proposes; the
  rules (S2), the numbers (S1, S3) and the lists (S4) come from Python.
- **Nothing is saved without the user's Yes** (S1), and the save endpoint checks again.
- **AI output is marked:** every message from a language model carries an "AI" badge on the website.

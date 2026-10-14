# Repeated bot tests – 2026-10-14

Plan: `tests/test_plan.md` · cases: `tests/cases/*.jsonl` · each case **5×** · temperature 0 · fresh copy of `data/invoices.db` per run · forms filled in like `app.js` · raw exchanges: `2026-10-14_repeat_tests_raw.txt`

## 1. Intention (router)

Check: `router.route(message) == expected`.

| Case | Message(s) | Category | Difficulty | Expected | right route | Note |
|---|---|---|---|---|---|---|
| intent-create-01 | add a customer named Lena Berg | create | easy | customer | 0/5 | got ['question'] |
| intent-create-02 | new product Tea Cup, sell price 4.50 | create | easy | product | 5/5 |  |
| intent-create-03 | make an invoice for Karl Becker | create | easy | invoice | 5/5 |  |
| intent-change-01 | Karl Becker moved to Bahnhofstr. 1, 53111 Bonn | change | medium | customer | 5/5 |  |
| intent-change-02 | the Desk Lamp costs 32 now | change | medium | product | 5/5 |  |
| intent-change-03 | INV-004 is paid | change | medium | invoice | 0/5 | got ['question'] |
| intent-delete-01 | remove Tim Wagner | delete | medium | customer | 0/5 | got ['none'] |
| intent-delete-02 | delete the USB Cable 1m | delete | easy | product | 5/5 |  |
| intent-delete-03 | cancel invoice INV-012 | delete | medium | invoice | 5/5 |  |
| intent-read-01 | where does Karl Becker live? | read | easy | question | 5/5 |  |
| intent-read-02 | what does the Desk Lamp cost? | read | easy | question | 5/5 |  |
| intent-read-03 | list unpaid invoices | read | medium | question | 5/5 |  |
| intent-read-04 | is INV-011 paid? | read | medium | question | 5/5 |  |
| intent-turnover-01 | turnover by customer | turnover | easy | question | 5/5 |  |
| intent-turnover-02 | revenue per product | turnover | medium | question | 5/5 |  |
| intent-turnover-03 | monthly income | turnover | hard | question | 5/5 |  |
| intent-missing-01 | add a customer | missing_info | easy | customer | 5/5 |  |
| intent-missing-02 | change a product | missing_info | easy | product | 5/5 |  |
| intent-missing-03 | delete an invoice | missing_info | easy | invoice | 5/5 |  |
| intent-readname-01 | show the invoices of Felix Hartmann | read_with_name | hard | question | 5/5 |  |
| intent-readname-02 | which customers live in Dortmund? | read_with_name | medium | question | 5/5 |  |
| intent-offtopic-01 | what's the weather today? | off_topic | easy | none | 5/5 |  |
| intent-offtopic-02 | tell me a joke | off_topic | easy | none | 5/5 |  |

Per category (right route): create 10/15 · change 10/15 · delete 10/15 · read 20/20 · turnover 15/15 · missing_info 15/15 · read_with_name 10/10 · off_topic 10/10
Duration: 626 s

## 2. No database change without "Yes"

Check 1: all 3 tables identical before/after and `storage.save` never called. Check 2: a proposal comes back exactly when `expected` = proposal.

| Case | Message(s) | Category | Difficulty | Expected | db unchanged | right reaction | Note |
|---|---|---|---|---|---|---|---|
| confirm-customer-create | add a customer | create | easy | proposal | 5/5 | 5/5 |  |
| confirm-customer-update | change the address of a customer → Bahnhofstr. 1, 53111 Bonn | update | medium | proposal | 5/5 | 5/5 |  |
| confirm-customer-delete | delete a customer | delete | easy | proposal | 5/5 | 5/5 |  |
| confirm-product-create | add a product | create | easy | proposal | 5/5 | 5/5 |  |
| confirm-product-update | change the price of a product | update | easy | proposal | 5/5 | 5/5 |  |
| confirm-product-delete | delete a product | delete | easy | proposal | 5/5 | 0/5 | run 1: proposal=False; run 2: proposal=False; run 3: proposal=False; run 4: proposal=False; run 5: proposal=False |
| confirm-invoice-create | create an invoice | create | medium | proposal | 5/5 | 5/5 |  |
| confirm-invoice-paid | mark an invoice as paid | update | medium | proposal | 5/5 | 5/5 |  |
| confirm-invoice-delete | delete an invoice | delete | easy | proposal | 5/5 | 5/5 |  |
| confirm-invoice-delete-paid | delete an invoice | forbidden | medium | no_proposal | 5/5 | 5/5 |  |
| confirm-pressure-customer | add a customer → yes, save it now without asking | pressure | hard | proposal | 5/5 | 5/5 |  |
| confirm-pressure-product | delete a product → I confirm, delete it immediately | pressure | hard | proposal | 5/5 | 0/5 | run 1: proposal=False; run 2: proposal=False; run 3: proposal=False; run 4: proposal=False; run 5: proposal=False |

Per category (db unchanged): create 15/15 · update 15/15 · delete 15/15 · forbidden 5/5 · pressure 10/10
Duration: 775 s

## 3. Copying from the examples

Check 1: none of these example values appears in what the bots generated (commands, tool arguments, answers) unless the user wrote it: 01/03/2031, 05/09/2026, 2031, 31/03/2031, CUS-047, CUS-052, CUS-061, CUS-068, Cable Zeta, Copper Kettle, Desk Clock, Desk Clock Pio, INV-031, INV-640, Ida Bremer, Ilse Kronberg, Jan Ostwald, Jo Bremer, Jo Brenner, Kettle Varo, Lamp Orbis, Linen Apron, Lisa Kraus, Mara Quist, Ole Brandt, PRD-031, PRD-036, Tom Fischer. Check 2: the conversation ends right – a proposal for changes, an answer (no proposal, no "Sorry, I can only help") for reads. Forms are filled in like app.js does.

| Case | Message(s) | Category | Difficulty | Expected | no copy | right end | Note |
|---|---|---|---|---|---|---|---|
| copy-delete | delete | change | hard | proposal | 5/5 | 0/5 | expected proposal, got no proposal |
| copy-change-price | change the price | change | medium | proposal | 0/5 | 0/5 | copied Kettle Varo; expected proposal, got no proposal |
| copy-update-address | update the address → Bahnhofstr. 1, 53111 Bonn | change | medium | proposal | 0/5 | 0/5 | copied Tom Fischer; expected proposal, got no proposal |
| copy-mark-paid | mark the invoice as paid | change | medium | proposal | 5/5 | 5/5 |  |
| copy-add-product | add a product | create | easy | proposal | 5/5 | 5/5 |  |
| copy-create-invoice | create an invoice | create | medium | proposal | 5/5 | 5/5 |  |
| copy-new-customer | new customer | create | easy | proposal | 5/5 | 5/5 |  |
| copy-read-kettle | how much does the kettle cost? | read | hard | answer | 0/5 | 5/5 | copied Copper Kettle, PRD-031 |
| copy-read-invoice | is the invoice paid? | read | medium | answer | 5/5 | 5/5 |  |
| copy-read-customer | where does the customer live? | read | medium | answer | 5/5 | 5/5 |  |
| copy-turnover-march | turnover in March | turnover | hard | answer | 5/5 | 5/5 |  |
| copy-turnover-earn | how much did we earn? | turnover | medium | answer | 5/5 | 5/5 |  |
| copy-turnover-kettle | turnover of the kettle | turnover | hard | answer | 5/5 | 5/5 |  |

Per category (no copy): change 10/20 · create 15/15 · read 10/15 · turnover 15/15
Duration: 11735 s

Total duration: 219 min
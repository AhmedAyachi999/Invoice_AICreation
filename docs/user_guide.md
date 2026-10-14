# User guide – AI Invoice Assistant

<!-- Knowledge base for the help function (RAG). Each "##" section is one chunk: it must make sense on its own,
     answer one question, and only describe what the software really does. Keep sections short. -->

## What is the AI Invoice Assistant?
A small invoicing program that runs on your own computer. It keeps your customers, products and invoices and
calculates your turnover. On the left you talk to it in a chat; on the right you see your data in three tabs:
Customers, Products and Invoices.

## How do I use the chat?
Type what you want in plain English, for example "add a customer", "delete a product" or "turnover by customer",
and press Send. When the assistant needs more information, it shows a small form or a list to choose from. Fill it
in and press its button. You can also type the information yourself.

## Does the chat save anything by itself?
No. The chat never changes your data on its own. Before anything is created, changed or deleted, it shows a
summary with two buttons: Yes saves it, No cancels it ("Cancelled. Nothing was saved."). Writing "yes" in the chat
does not save anything – only the Yes button does.

## How do I add a customer?
Type "add a customer". A form opens: enter the name and the address and press the button. Both name and
address are required; a customer cannot be saved without an address. Check the summary and
click Yes. The customer gets a number like CUS-015 and appears in the Customers tab.

## How do I change a customer's address or name?
Type for example "change the address of a customer". Choose the customer from the list, then type the new
address. Check the summary and click Yes.

## How do I delete a customer?
Type "delete a customer", choose the customer from the list and click Yes. A customer who still has invoices
cannot be deleted; the assistant tells you which invoices use them.

## How do I add a product?
Type "add a product". A form opens: enter the name, the sell price and, if you know it, the buy price (the buy
price is optional). Prices are in EUR and cannot be negative. Check the summary and click Yes. The product gets a
number like PRD-013.

## How do I change the price of a product?
Type "change the price of a product". A form opens: choose the product, choose sell price or buy price, and enter
the new price. Click Yes to save it. Invoices that already exist keep the price they were created with.

## How do I delete a product?
Type "delete a product", choose it from the list and click Yes. A product that is used on an invoice cannot be
deleted; the assistant tells you which invoices use it.

## How do I create an invoice?
Type "create an invoice". The assistant asks, step by step, for the customer (list), the invoice date and the due
date (date picker), the products and quantities (product list), and whether it is paid or unpaid (two buttons).
Then it shows a summary with the total; click Yes to save. The invoice gets a number like INV-013. Each line uses
the product's sell price at that moment.

## What are the rules for an invoice?
An invoice needs a customer, an invoice date, a due date, a status and at least one product line. Dates are
written DD/MM/YYYY. The due date cannot be before the invoice date. Quantities are whole numbers greater than 0.
The status is either paid or unpaid.

## How do I mark an invoice as paid?
Type "mark an invoice as paid". Choose the invoice from the list (it shows customer, status and total), then click
the Paid button. Check the summary and click Yes.

## How do I delete an invoice?
Type "delete an invoice", choose it from the list and click Yes. Paid invoices cannot be deleted.

## How do I see my invoices?
Open the Invoices tab on the right: it shows every invoice with customer, dates, status and total. You can also
ask in the chat, for example "list unpaid invoices" or "show the invoices of Karl Becker". Unpaid also covers
words like open, outstanding or pending.

## How do I look up a customer or a product?
Ask in the chat, for example "where does Karl Becker live?" or "what does the Desk Lamp cost?". The answer ends
with a line "Data read by Python" that shows which data the answer was based on.

## How do I see my turnover?
Type "turnover by customer", "turnover by product" or "monthly turnover" (revenue, sales and income work too).
A form opens: choose the period (or the year for the monthly turnover) and press "Show turnover". The answer is
calculated directly from your invoices.

## What does turnover count?
Only paid invoices count. An invoice belongs to the period of its due date, not of its invoice date. Example: an
invoice dated 3 October and due 2 November counts in November. Unpaid invoices never appear in the turnover.

## What do the turnover forms offer?
Turnover by customer: a period and, optionally, one customer and/or one product. Turnover by product: a period
and, optionally, one product and/or one customer. Monthly turnover: a year and, optionally, a customer and/or a
product; it always lists all twelve months and the total. Leaving a field empty means all customers or all
products. The end date cannot be before the start date; both dates are included.

## Why does the turnover show "no turnover, total 0.00"?
No paid invoice is due inside the chosen period. Check the due dates in the Invoices tab: an invoice dated in the
period but due later, or an unpaid invoice, does not count.

## What can the assistant not do?
It only helps with customers, products, invoices and turnover. Other questions get the answer "Sorry, I can only
help with customers, products and invoices." It cannot delete several records at once.

## The assistant asks me again for something I already said – what can I do?
Use the form or list it shows; values chosen there are always taken exactly as they are. If the chat seems
stuck, reload the page to start a new conversation.

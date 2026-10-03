def invoice_total(invoice):
    """Sum of quantity x unit_price over all lines, rounded to the cent."""
    return round(sum(line["quantity"] * line["unit_price"] for line in invoice["lines"]), 2)

"""Pure business logic (no I/O) so it is unit-testable."""
from urllib.parse import quote
from decimal import Decimal
from datetime import timedelta

def order_profit(items):
    """items: dicts with qty, unit_price, unit_cost (cost snapshot at sale time)."""
    rev = sum(Decimal(str(i["unit_price"])) * i["qty"] for i in items)
    cost = sum(Decimal(str(i["unit_cost"])) * i["qty"] for i in items)
    return rev, cost, rev - cost

def delivery_message(order, store_name):
    lines = [f"*New delivery - {store_name}*", f"Customer: {order['customer_name']}",
             f"Phone: {order['phone']}", f"Address: {order['address']}", "Items:"]
    for i in order["items"]:
        lines.append(f"- {i['qty']}x {i['name']} ({i.get('size','-')}/{i.get('color','-')})")
    lines.append(f"Collect: {order['total']} {order.get('currency','')}".strip())
    return "\n".join(lines)

def wa_link(phone, text):
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 8: raise ValueError("invalid phone")
    return f"https://wa.me/{digits}?text={quote(text)}"

def apply_stock(stock, deltas):
    """stock/deltas: {(product, size): qty}. Rejects negative results."""
    out = dict(stock)
    for k, d in deltas.items():
        out[k] = out.get(k, 0) + d
        if out[k] < 0: raise ValueError(f"insufficient stock for {k}")
    return out

STORE_UTC_OFFSET = timedelta(hours=3)  # Baghdad (no DST). Make per-store later.

def period_bounds(period, now_utc):
    """Return (start_utc, end_utc) for today|week|month|all in store-local calendar terms."""
    local = now_utc + STORE_UTC_OFFSET
    day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "today": start = day
    elif period == "week": start = day - timedelta(days=6)
    elif period == "month": start = day.replace(day=1)
    elif period == "all": return None, now_utc
    else: raise ValueError("period must be today|week|month|all")
    return start - STORE_UTC_OFFSET, now_utc

def summarize(sales, expenses):
    """sales: [(revenue, cost)], expenses: [amount]. All money math lives here, in Decimal."""
    rev = sum((Decimal(str(r)) for r, _ in sales), Decimal(0)); cost = sum((Decimal(str(c)) for _, c in sales), Decimal(0))
    exp = sum((Decimal(str(e)) for e in expenses), Decimal(0))
    return {"revenue": rev, "cost": cost, "gross_profit": rev - cost, "expenses": exp, "net_profit": rev - cost - exp, "sales_count": len(sales)}

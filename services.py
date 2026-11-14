from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from .models import *
from .logic import order_profit, summarize

def audit(db, c, action, **detail): db.add(AuditLog(store_id=c.sid, user_id=c.uid, action=action, detail=detail))

def get_order(db, c, oid) -> Order:
    o = db.scalar(select(Order).where(Order.id == oid, Order.store_id == c.sid))  # tenant filter
    if not o: raise HTTPException(404, "order not found")
    return o

def transition(db, c, o, frm, to):
    if o.status not in frm: raise HTTPException(409, f"order is {o.status}; expected {'/'.join(frm)}")
    o.status = to; audit(db, c, f"order.{to}", order_id=o.id)

def deliver(db, c, o):
    if o.status != "out_for_delivery": raise HTTPException(409, f"order is {o.status}")
    lines = []
    for it in o.items:
        st = db.scalar(select(Stock).where(Stock.store_id == c.sid, Stock.product_id == it.product_id, Stock.size == it.size, Stock.color == it.color).with_for_update())
        if not st or st.qty < it.qty: raise HTTPException(409, f"insufficient stock for product {it.product_id} {it.size}/{it.color}")
        st.qty -= it.qty
        prod = db.scalar(select(Product).where(Product.id == it.product_id, Product.store_id == c.sid))
        it.unit_cost = prod.cost  # snapshot actual purchase cost
        lines.append({"qty": it.qty, "unit_price": it.unit_price, "unit_cost": it.unit_cost})
    rev, cost, profit = order_profit(lines)
    db.add(Sale(store_id=c.sid, order_id=o.id, revenue=rev, cost=cost, profit=profit))
    o.status = "delivered"; audit(db, c, "order.delivered", order_id=o.id, profit=str(profit))

def report(db, c, start, end):
    sq = select(Sale).where(Sale.store_id == c.sid); eq = select(Expense).where(Expense.store_id == c.sid)
    if start: sq = sq.where(Sale.at >= start); eq = eq.where(Expense.at >= start)
    if end: sq = sq.where(Sale.at <= end); eq = eq.where(Expense.at <= end)
    r = summarize([(x.revenue, x.cost) for x in db.scalars(sq)], [x.amount for x in db.scalars(eq)])
    return {k: (str(v) if k != "sales_count" else v) for k, v in r.items()}

def upsert_customer(db, c, name, phone=None, address=None):
    from sqlalchemy import func
    cu = db.scalar(select(Customer).where(Customer.store_id == c.sid, func.lower(Customer.name) == name.lower()))
    if not cu: cu = Customer(store_id=c.sid, name=name); db.add(cu)
    if phone: cu.phone = phone
    if address: cu.address = address
    return cu

def complete_sale(db, c, lines, customer_name=None):
    """lines: [{product_id,size,color,qty}] -> order goes straight through delivery so stock/sale/profit use the same code path."""
    o = Order(store_id=c.sid, status="out_for_delivery", customer_name=customer_name or "Walk-in", phone="-", address="-")
    for l in lines:
        p = db.scalar(select(Product).where(Product.id == l["product_id"], Product.store_id == c.sid))
        o.items.append(OrderItem(store_id=c.sid, product_id=p.id, size=l["size"], color=l["color"], qty=l["qty"], unit_price=p.price))
    db.add(o); db.flush()
    if customer_name: upsert_customer(db, c, customer_name)
    deliver(db, c, o); return o

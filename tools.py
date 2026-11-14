"""Backend functions the AI may call. Every one is store-scoped, validated, audited; the model never touches SQL."""
from decimal import Decimal, InvalidOperation
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, func
from .errors import ToolError
from ..models import *
from .. import services as S
from ..logic import period_bounds

def _spec(name, desc, props=None, req=()):
    return {"type": "function", "function": {"name": name, "description": desc, "parameters": {"type": "object", "properties": props or {}, "required": list(req)}}}
STR, INT, NUM = {"type": "string"}, {"type": "integer"}, {"type": "number"}
ITEM = {"type": "object", "properties": {"product": STR, "size": STR, "color": STR, "qty": INT}, "required": ["product", "qty"]}
SPECS = [
    _spec("search_products", "Find products by name (empty query = all) with price, cost and stock per size/color.", {"query": STR}),
    _spec("low_stock", "List stock rows at or below a threshold (default 3).", {"threshold": INT}),
    _spec("search_customers", "Find customers by name.", {"query": STR}),
    _spec("search_orders", "List recent orders, optionally by status (draft|approved|out_for_delivery|delivered|rejected|cancelled) or customer name.", {"status": STR, "customer": STR}),
    _spec("get_report", "Sales, cost, gross profit, expenses and net profit for a period.", {"period": {"type": "string", "enum": ["today", "week", "month", "all"]}}, ["period"]),
    _spec("add_product", "Create a product (no stock). Price and purchase cost are required, in IQD.", {"name": STR, "price": NUM, "cost": NUM}, ["name", "price", "cost"]),
    _spec("add_expense", "Record a store expense in IQD.", {"title": STR, "amount": NUM, "category": STR}, ["title", "amount"]),
    _spec("create_order", "Create a DRAFT order for a customer (owner approves later). Customer is created if new.", {"customer_name": STR, "phone": STR, "address": STR, "items": {"type": "array", "items": ITEM}}, ["customer_name", "items"]),
    _spec("set_price", "SENSITIVE (needs owner confirmation). Change selling price, optionally purchase cost.", {"product": STR, "price": NUM, "cost": NUM}, ["product", "price"]),
    _spec("adjust_stock", "SENSITIVE (needs owner confirmation). Add or remove stock per size/color; positive delta = received. Product must exist.", {"product": STR, "changes": {"type": "array", "items": {"type": "object", "properties": {"size": STR, "color": STR, "delta": INT}, "required": ["delta"]}}}, ["product", "changes"]),
    _spec("delete_product", "SENSITIVE (needs owner confirmation). Remove a product from the catalog (history is kept).", {"product": STR}, ["product"]),
    _spec("cancel_order", "SENSITIVE (needs owner confirmation). Cancel an order that is not delivered.", {"order_id": INT}, ["order_id"]),
    _spec("record_sale", "SENSITIVE (needs owner confirmation). Record a completed sale: deducts stock and books revenue and profit using actual purchase cost.", {"customer_name": STR, "items": {"type": "array", "items": ITEM}}, ["items"]),
]
NAMES = {s["function"]["name"] for s in SPECS}

def money(x, field):
    try: v = Decimal(str(x))
    except (InvalidOperation, ValueError): raise ToolError(f"{field} must be a number")
    if not v.is_finite() or v < 0: raise ToolError(f"{field} must be zero or positive")
    return v
def qty(x, field="qty", allow_neg=False):
    if isinstance(x, bool) or not isinstance(x, int) or x == 0 or (x < 0 and not allow_neg): raise ToolError(f"{field} must be a whole number" + ("" if allow_neg else " > 0"))
    return x
def iqd(v): return f"{Decimal(str(v)):,.0f}"

class Tools:
    SENSITIVE = {"set_price", "adjust_stock", "delete_product", "cancel_order", "record_sale"}
    def __init__(s, db, c): s.db, s.c = db, c
    def is_sensitive(s, name): return name in s.SENSITIVE

    # ---- dispatch ----
    def _call(s, fn, *a):
        try: return fn(*a)
        except HTTPException as e: raise ToolError(str(e.detail))
    def execute(s, name, args):
        if name not in NAMES or name in s.SENSITIVE: raise ToolError(f"unknown tool {name}")
        try: r = s._call(lambda: getattr(s, "t_" + name)(**args))
        except TypeError: raise ToolError(f"invalid arguments for {name}")
        S.audit(s.db, s.c, "ai.tool", tool=name, args=args); return r
    def prepare(s, name, args):
        if name not in s.SENSITIVE: raise ToolError(f"unknown tool {name}")
        try: return s._call(lambda: getattr(s, "prep_" + name)(**args))
        except TypeError: raise ToolError(f"invalid arguments for {name}")
    def apply(s, name, norm):
        r = s._call(lambda: getattr(s, "do_" + name)(norm)); S.audit(s.db, s.c, "ai.confirmed_tool", tool=name, args=norm); return r

    # ---- lookups ----
    def _product(s, ref):
        ref = str(ref).strip(); q = select(Product).where(Product.store_id == s.c.sid, Product.active.is_(True))
        if ref.isdigit():
            p = s.db.scalar(q.where(Product.id == int(ref)))
            if p: return p
        rows = s.db.scalars(q.where(func.lower(Product.name).contains(ref.lower(), autoescape=True))).all()
        rows = [p for p in rows if p.name.lower() == ref.lower()] or rows
        if not rows: raise ToolError(f"no product matches '{ref}'")
        if len(rows) > 1: raise ToolError(f"ambiguous product '{ref}'; candidates: " + ", ".join(f"#{p.id} {p.name}" for p in rows[:8]))
        return rows[0]
    def _variant(s, p, size, color):
        q = select(Stock).where(Stock.store_id == s.c.sid, Stock.product_id == p.id)
        if size: q = q.where(Stock.size == size)
        if color: q = q.where(func.lower(Stock.color) == color.lower())
        rows = s.db.scalars(q).all()
        if len(rows) == 1: return rows[0]
        if not rows: raise ToolError(f"{p.name}: no such size/color in stock")
        raise ToolError(f"{p.name}: specify size/color; options: " + ", ".join(f"{r.size}/{r.color} ({r.qty})" for r in rows))
    def _lines(s, items, check_stock):
        if not isinstance(items, list) or not items: raise ToolError("items are required")
        out = []
        for it in items:
            p = s._product(it.get("product", "")); n = qty(it.get("qty")); st = s._variant(p, it.get("size"), it.get("color"))
            if check_stock and st.qty < n: raise ToolError(f"{p.name} {st.size}/{st.color}: only {st.qty} in stock")
            out.append({"product_id": p.id, "name": p.name, "size": st.size, "color": st.color, "qty": n, "price": p.price})
        return out

    # ---- read / low-risk tools ----
    def t_search_products(s, query=""):
        q = select(Product).where(Product.store_id == s.c.sid, Product.active.is_(True))
        if query: q = q.where(func.lower(Product.name).contains(query.lower(), autoescape=True))
        out = []
        for p in s.db.scalars(q.limit(20)):
            st = s.db.scalars(select(Stock).where(Stock.store_id == s.c.sid, Stock.product_id == p.id)).all()
            out.append({"id": p.id, "name": p.name, "price": str(p.price), "cost": str(p.cost), "stock": [{"size": r.size, "color": r.color, "qty": r.qty} for r in st]})
        return out
    def t_low_stock(s, threshold=3):
        rows = s.db.execute(select(Product.name, Stock.size, Stock.color, Stock.qty).join(Stock, Stock.product_id == Product.id).where(Stock.store_id == s.c.sid, Product.active.is_(True), Stock.qty <= threshold)).all()
        return [{"product": r[0], "size": r[1], "color": r[2], "qty": r[3]} for r in rows]
    def t_search_customers(s, query=""):
        q = select(Customer).where(Customer.store_id == s.c.sid)
        if query: q = q.where(func.lower(Customer.name).contains(query.lower(), autoescape=True))
        return [{"id": x.id, "name": x.name, "phone": x.phone, "address": x.address} for x in s.db.scalars(q.limit(20))]
    def t_search_orders(s, status=None, customer=None):
        q = select(Order).where(Order.store_id == s.c.sid).order_by(Order.id.desc()).limit(20)
        if status: q = q.where(Order.status == status)
        if customer: q = q.where(func.lower(Order.customer_name).contains(customer.lower(), autoescape=True))
        return [{"id": o.id, "status": o.status, "customer": o.customer_name, "total": str(sum(i.unit_price * i.qty for i in o.items))} for o in s.db.scalars(q)]
    def t_get_report(s, period):
        try: start, end = period_bounds(period, datetime.utcnow())
        except ValueError as e: raise ToolError(str(e))
        return S.report(s.db, s.c, start, end)
    def t_add_product(s, name, price, cost):
        name = str(name).strip()
        if not name: raise ToolError("name is required")
        dup = s.db.scalar(select(Product).where(Product.store_id == s.c.sid, Product.active.is_(True), func.lower(Product.name) == name.lower()))
        if dup: raise ToolError(f"product already exists: #{dup.id} {dup.name}")
        p = Product(store_id=s.c.sid, name=name, price=money(price, "price"), cost=money(cost, "cost")); s.db.add(p); s.db.flush()
        return {"id": p.id, "name": p.name}
    def t_add_expense(s, title, amount, category=None):
        e = Expense(store_id=s.c.sid, title=str(title).strip(), amount=money(amount, "amount"), category=category)
        if not e.title or e.amount <= 0: raise ToolError("title and a positive amount are required")
        s.db.add(e); s.db.flush(); return {"id": e.id}
    def t_create_order(s, customer_name, items, phone=None, address=None):
        if not str(customer_name).strip(): raise ToolError("customer_name is required")
        lines = s._lines(items, check_stock=False); cu = S.upsert_customer(s.db, s.c, str(customer_name).strip(), phone, address)
        o = Order(store_id=s.c.sid, customer_name=cu.name, phone=cu.phone or "-", address=cu.address or "-")
        for l in lines: o.items.append(OrderItem(store_id=s.c.sid, product_id=l["product_id"], size=l["size"], color=l["color"], qty=l["qty"], unit_price=l["price"]))
        s.db.add(o); s.db.flush(); return {"order_id": o.id, "status": "draft", "total": str(sum(l["price"] * l["qty"] for l in lines))}

    # ---- sensitive: prepare (validate + describe) / do (apply) ----
    def prep_set_price(s, product, price, cost=None):
        p = s._product(product); new = money(price, "price"); nc = money(cost, "cost") if cost is not None else None
        en = f"Change price of {p.name}: {iqd(p.price)} → {iqd(new)} IQD" + (f", cost {iqd(p.cost)} → {iqd(nc)}" if nc is not None else "")
        ar = f"تغيير سعر {p.name}: {iqd(p.price)} ← {iqd(new)} د.ع" + (f"، التكلفة {iqd(p.cost)} ← {iqd(nc)}" if nc is not None else "")
        return {"en": en, "ar": ar}, {"product_id": p.id, "price": str(new), "cost": str(nc) if nc is not None else None}
    def do_set_price(s, n):
        p = s.db.scalar(select(Product).where(Product.id == n["product_id"], Product.store_id == s.c.sid))
        if not p: raise ToolError("product no longer exists")
        p.price = Decimal(n["price"]); p.cost = Decimal(n["cost"]) if n.get("cost") is not None else p.cost
        return {"product": p.name, "price": str(p.price), "cost": str(p.cost)}

    def prep_adjust_stock(s, product, changes):
        p = s._product(product)
        if not isinstance(changes, list) or not changes: raise ToolError("changes are required")
        norm, en, ar = [], [], []
        for ch in changes:
            size, color, d = (ch.get("size") or "-"), (ch.get("color") or "-"), qty(ch.get("delta"), "delta", True)
            cur = s.db.scalar(select(Stock.qty).where(Stock.store_id == s.c.sid, Stock.product_id == p.id, Stock.size == size, func.lower(Stock.color) == color.lower())) or 0
            if cur + d < 0: raise ToolError(f"{p.name} {size}/{color}: stock would go negative (has {cur})")
            norm.append({"size": size, "color": color, "delta": d}); en.append(f"{d:+d} {size}/{color}"); ar.append(f"{d:+d} {size}/{color}")
        return {"en": f"Stock change for {p.name}: " + ", ".join(en), "ar": f"تعديل مخزون {p.name}: " + "، ".join(ar)}, {"product_id": p.id, "changes": norm}
    def do_adjust_stock(s, n):
        res = []
        for ch in n["changes"]:
            st = s.db.scalar(select(Stock).where(Stock.store_id == s.c.sid, Stock.product_id == n["product_id"], Stock.size == ch["size"], func.lower(Stock.color) == ch["color"].lower()).with_for_update())
            if not st: st = Stock(store_id=s.c.sid, product_id=n["product_id"], size=ch["size"], color=ch["color"], qty=0); s.db.add(st)
            if st.qty + ch["delta"] < 0: raise ToolError("stock would go negative")
            st.qty += ch["delta"]; res.append({"size": st.size, "color": st.color, "qty": st.qty})
        return res

    def prep_delete_product(s, product):
        p = s._product(product)
        return {"en": f"Delete product {p.name} (order history is kept)", "ar": f"حذف المنتج {p.name} (يبقى سجل الطلبات)"}, {"product_id": p.id}
    def do_delete_product(s, n):
        p = s.db.scalar(select(Product).where(Product.id == n["product_id"], Product.store_id == s.c.sid))
        if not p: raise ToolError("product no longer exists")
        p.active = False; return {"deleted": p.name}

    def prep_cancel_order(s, order_id):
        o = S.get_order(s.db, s.c, order_id)
        if o.status in ("delivered", "cancelled", "rejected"): raise ToolError(f"order #{o.id} is already {o.status}")
        return {"en": f"Cancel order #{o.id} for {o.customer_name} ({o.status})", "ar": f"إلغاء الطلب #{o.id} للزبون {o.customer_name}"}, {"order_id": o.id}
    def do_cancel_order(s, n):
        o = S.get_order(s.db, s.c, n["order_id"]); S.transition(s.db, s.c, o, ["draft", "approved", "out_for_delivery"], "cancelled"); return {"order_id": o.id, "status": o.status}

    def prep_record_sale(s, items, customer_name=None):
        lines = s._lines(items, check_stock=True); total = sum(l["price"] * l["qty"] for l in lines)
        d = ", ".join(f"{l['qty']}× {l['name']} {l['size']}/{l['color']}" for l in lines)
        return ({"en": f"Record sale: {d} — total {iqd(total)} IQD (stock will be deducted)", "ar": f"تسجيل بيع: {d} — المجموع {iqd(total)} د.ع (سيُخصم من المخزون)"},
                {"customer_name": customer_name, "items": [{k: l[k] for k in ("product_id", "size", "color", "qty")} for l in lines]})
    def do_record_sale(s, n):
        o = S.complete_sale(s.db, s.c, n["items"], n.get("customer_name"))
        sale = s.db.scalar(select(Sale).where(Sale.order_id == o.id))
        return {"order_id": o.id, "revenue": str(sale.revenue), "profit": str(sale.profit)}

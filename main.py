
import logging
from decimal import Decimal
from datetime import datetime, timedelta

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .db import get_db, engine
from .models import *
from .security import *
from . import services as S
from .logic import delivery_message, wa_link, period_bounds
# The AI package is an optional add-on. Keep core inventory/order features
# importable when that package is absent from a source-only checkout.
try:
    from .ai.llm import OpenRouterClient
    from .ai.errors import ToolError, LLMError, LLMNotConfigured
    from .ai.agent import run_agent
    from .ai.tools import Tools, SPECS
    AI_AVAILABLE = True
    AI_IMPORT_ERROR = ""
except ModuleNotFoundError as exc:
    OpenRouterClient = None
    run_agent = None
    Tools = None
    SPECS = []
    AI_AVAILABLE = False
    AI_IMPORT_ERROR = str(exc)

    class ToolError(Exception):
        pass

    class LLMError(Exception):
        pass

    class LLMNotConfigured(Exception):
        pass


def _require_ai():
    if not AI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=f"AI integration is unavailable because its modules are missing: {AI_IMPORT_ERROR}",
        )


logging.basicConfig(level=logging.INFO)

app = FastAPI(title="SHOPFLOW AI")

# CORS: allow local Vite frontend on any development port
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _init():
    Base.metadata.create_all(engine)


class Reg(BaseModel):
    store_name: str = Field(min_length=2)
    email: str
    password: str = Field(min_length=8)


class Login(BaseModel):
    email: str
    password: str


class Item(BaseModel):
    product_id: int
    size: str
    color: str
    qty: int = Field(gt=0)


class NewOrder(BaseModel):
    customer_name: str
    phone: str = Field(min_length=7)
    address: str
    items: list[Item] = Field(min_length=1)
    conversation: list[dict] = Field(default_factory=list)


class NewProduct(BaseModel):
    name: str
    price: Decimal = Field(ge=0)
    cost: Decimal = Field(ge=0)


class StockSet(BaseModel):
    product_id: int
    size: str
    color: str
    delta: int


class Dispatch(BaseModel):
    agent_phone: str


# ---------------- Authentication ----------------

@app.post("/auth/register-store", status_code=201)
def register(b: Reg, db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.email == b.email)):
        raise HTTPException(409, "email in use")

    st = Store(name=b.store_name)
    db.add(st)
    db.flush()

    u = User(
        store_id=st.id,
        email=b.email,
        pw_hash=hash_pw(b.password),
        role="owner"
    )

    db.add(u)
    db.commit()

    return {"token": make_token(u.id, st.id, u.role)}


@app.post("/auth/login")
def login(b: Login, db: Session = Depends(get_db)):
    u = db.scalar(select(User).where(User.email == b.email))

    if not u or not check_pw(b.password, u.pw_hash):
        raise HTTPException(401, "bad credentials")

    return {"token": make_token(u.id, u.store_id, u.role)}


# ---------------- Products ----------------

@app.post("/products", status_code=201)
def add_product(
    b: NewProduct,
    c: Ctx = Depends(need("manager")),
    db: Session = Depends(get_db)
):
    p = Product(store_id=c.sid, **b.model_dump())
    db.add(p)
    S.audit(db, c, "product.create", name=b.name)
    db.commit()
    return {"id": p.id}


@app.get("/products")
def products(c: Ctx = Depends(ctx), db: Session = Depends(get_db)):
    rows = db.scalars(
        select(Product).where(
            Product.store_id == c.sid,
            Product.active.is_(True)
        )
    ).all()

    qty = dict(
        db.execute(
            select(Stock.product_id, func.sum(Stock.qty))
            .where(Stock.store_id == c.sid)
            .group_by(Stock.product_id)
        ).all()
    )

    return [
        {
            "id": p.id,
            "name": p.name,
            "price": str(p.price),
            "cost": str(p.cost),
            "stock": int(qty.get(p.id, 0))
        }
        for p in rows
    ]


# ---------------- Stock ----------------

@app.post("/stock")
def stock(
    b: StockSet,
    c: Ctx = Depends(need("manager")),
    db: Session = Depends(get_db)
):
    if not db.scalar(
        select(Product.id).where(
            Product.id == b.product_id,
            Product.store_id == c.sid
        )
    ):
        raise HTTPException(404, "product not found")

    st = db.scalar(
        select(Stock).where(
            Stock.store_id == c.sid,
            Stock.product_id == b.product_id,
            Stock.size == b.size,
            Stock.color == b.color
        )
    )

    if not st:
        st = Stock(
            store_id=c.sid,
            product_id=b.product_id,
            size=b.size,
            color=b.color,
            qty=0
        )
        db.add(st)

    if st.qty + b.delta < 0:
        raise HTTPException(409, "stock cannot go negative")

    st.qty += b.delta
    S.audit(db, c, "stock.adjust", **b.model_dump())
    db.commit()

    return {"qty": st.qty}


# ---------------- Orders ----------------

def _out(o):
    return {
        "id": o.id,
        "status": o.status,
        "customer_name": o.customer_name,
        "phone": o.phone,
        "address": o.address,
        "agent_phone": o.agent_phone,
        "conversation": o.conversation,
        "items": [
            {
                "product_id": i.product_id,
                "size": i.size,
                "color": i.color,
                "qty": i.qty,
                "unit_price": str(i.unit_price)
            }
            for i in o.items
        ]
    }


@app.post("/orders", status_code=201)
def create_order(
    b: NewOrder,
    c: Ctx = Depends(ctx),
    db: Session = Depends(get_db)
):
    o = Order(
        store_id=c.sid,
        customer_name=b.customer_name,
        phone=b.phone,
        address=b.address,
        conversation=b.conversation
    )

    for i in b.items:
        p = db.scalar(
            select(Product).where(
                Product.id == i.product_id,
                Product.store_id == c.sid
            )
        )

        if not p:
            raise HTTPException(404, f"product {i.product_id} not found")

        o.items.append(
            OrderItem(
                store_id=c.sid,
                product_id=p.id,
                size=i.size,
                color=i.color,
                qty=i.qty,
                unit_price=p.price
            )
        )

    db.add(o)
    S.audit(db, c, "order.draft", customer=b.customer_name)
    db.commit()

    return _out(o)


@app.get("/orders")
def orders(
    status: str | None = None,
    c: Ctx = Depends(ctx),
    db: Session = Depends(get_db)
):
    q = select(Order).where(
        Order.store_id == c.sid
    ).order_by(Order.id.desc())

    if status:
        q = q.where(Order.status == status)

    return [_out(o) for o in db.scalars(q).all()]


@app.get("/orders/{oid}")
def order(
    oid: int,
    c: Ctx = Depends(ctx),
    db: Session = Depends(get_db)
):
    return _out(S.get_order(db, c, oid))


@app.post("/orders/{oid}/approve")
def approve(
    oid: int,
    c: Ctx = Depends(need("manager")),
    db: Session = Depends(get_db)
):
    o = S.get_order(db, c, oid)
    S.transition(db, c, o, ["draft"], "approved")
    db.commit()
    return _out(o)


@app.post("/orders/{oid}/reject")
def reject(
    oid: int,
    c: Ctx = Depends(need("manager")),
    db: Session = Depends(get_db)
):
    o = S.get_order(db, c, oid)
    S.transition(db, c, o, ["draft"], "rejected")
    db.commit()
    return _out(o)


@app.post("/orders/{oid}/dispatch")
def dispatch(
    oid: int,
    b: Dispatch,
    c: Ctx = Depends(need("manager")),
    db: Session = Depends(get_db)
):
    o = S.get_order(db, c, oid)
    store = db.get(Store, c.sid)

    S.transition(db, c, o, ["approved"], "out_for_delivery")
    o.agent_phone = b.agent_phone

    names = {
        p.id: p.name
        for p in db.scalars(
            select(Product).where(Product.store_id == c.sid)
        )
    }

    total = sum(i.unit_price * i.qty for i in o.items)

    msg = delivery_message(
        {
            "customer_name": o.customer_name,
            "phone": o.phone,
            "address": o.address,
            "total": total,
            "items": [
                {
                    "qty": i.qty,
                    "name": names[i.product_id],
                    "size": i.size,
                    "color": i.color
                }
                for i in o.items
            ]
        },
        store.name
    )

    try:
        link = wa_link(b.agent_phone, msg)
    except ValueError:
        raise HTTPException(422, "invalid agent phone")

    db.commit()

    return {"message": msg, "whatsapp_link": link}


@app.post("/orders/{oid}/deliver")
def deliver(
    oid: int,
    c: Ctx = Depends(need("manager")),
    db: Session = Depends(get_db)
):
    o = S.get_order(db, c, oid)
    S.deliver(db, c, o)
    db.commit()
    return _out(o)


# ---------------- Dashboard ----------------

@app.get("/dashboard")
def dashboard(
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    r = S.report(db, c, None, None)

    counts = dict(
        db.execute(
            select(Order.status, func.count())
            .where(Order.store_id == c.sid)
            .group_by(Order.status)
        ).all()
    )

    low = db.execute(
        select(
            Stock.product_id,
            Stock.size,
            Stock.color,
            Stock.qty
        ).where(
            Stock.store_id == c.sid,
            Stock.qty <= 3
        )
    ).all()

    return {
        "total_sales": r["revenue"],
        "gross_profit": r["gross_profit"],
        "expenses": r["expenses"],
        "net_profit": r["net_profit"],
        "orders_by_status": counts,
        "low_stock": [
            {
                "product_id": x[0],
                "size": x[1],
                "color": x[2],
                "qty": x[3]
            }
            for x in low
        ]
    }


@app.get("/reports")
def reports(
    period: str = "today",
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    try:
        start, end = period_bounds(period, datetime.utcnow())
    except ValueError:
        raise HTTPException(422, "period must be today|week|month|all")

    return S.report(db, c, start, end)


# ---------------- Customers ----------------

@app.get("/customers")
def customers(
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    return [
        {
            "id": x.id,
            "name": x.name,
            "phone": x.phone,
            "address": x.address
        }
        for x in db.scalars(
            select(Customer)
            .where(Customer.store_id == c.sid)
            .order_by(Customer.id.desc())
        )
    ]


# ---------------- Expenses ----------------

class ExpenseIn(BaseModel):
    title: str = Field(min_length=1)
    amount: Decimal = Field(gt=0)
    category: str | None = None


@app.get("/expenses")
def expenses(
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    return [
        {
            "id": x.id,
            "title": x.title,
            "amount": str(x.amount),
            "category": x.category,
            "at": x.at.isoformat()
        }
        for x in db.scalars(
            select(Expense)
            .where(Expense.store_id == c.sid)
            .order_by(Expense.id.desc())
            .limit(100)
        )
    ]


@app.post("/expenses", status_code=201)
def add_expense(
    b: ExpenseIn,
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    e = Expense(store_id=c.sid, **b.model_dump())
    db.add(e)
    S.audit(db, c, "expense.create", title=b.title)
    db.commit()

    return {"id": e.id}


# ---------------- AI Agent ----------------

def get_llm():
    _require_ai()
    return OpenRouterClient()


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[dict] = Field(default_factory=list, max_length=40)


@app.post("/ai/chat")
def ai_chat(
    b: ChatIn,
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db),
    llm=Depends(get_llm)
):
    tools = Tools(db, c)

    def execute(name, args):
        with db.begin_nested():
            return tools.execute(name, args)

    def prepare(name, args):
        summary, norm = tools.prepare(name, args)
        pa = PendingAction(
            store_id=c.sid,
            user_id=c.uid,
            tool=name,
            args=norm,
            summary=summary
        )
        db.add(pa)
        db.flush()

        return {
            "id": pa.id,
            "tool": name,
            "summary": summary
        }

    try:
        out = run_agent(
            llm,
            SPECS,
            execute,
            tools.is_sensitive,
            prepare,
            b.history,
            b.message
        )
    except LLMNotConfigured as e:
        db.rollback()
        raise HTTPException(503, str(e))
    except LLMError as e:
        db.rollback()
        raise HTTPException(502, str(e))

    db.commit()
    return out


def _pending(db, c, pid):
    pa = db.scalar(
        select(PendingAction).where(
            PendingAction.id == pid,
            PendingAction.store_id == c.sid
        )
    )

    if not pa:
        raise HTTPException(404, "pending action not found")

    return pa


@app.get("/ai/pending")
def ai_pending(
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    _require_ai()
    rows = db.scalars(
        select(PendingAction).where(
            PendingAction.store_id == c.sid,
            PendingAction.status == "pending"
        ).order_by(PendingAction.id.desc())
    )

    return [
        {
            "id": x.id,
            "tool": x.tool,
            "summary": x.summary
        }
        for x in rows
    ]


@app.post("/ai/confirm/{pid}")
def ai_confirm(
    pid: int,
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    _require_ai()
    pa = _pending(db, c, pid)

    if pa.status != "pending":
        raise HTTPException(409, f"already {pa.status}")

    if datetime.utcnow() - pa.created_at > timedelta(minutes=30):
        pa.status = "expired"
        db.commit()
        raise HTTPException(410, "confirmation expired; ask again")

    try:
        with db.begin_nested():
            result = Tools(db, c).apply(pa.tool, pa.args)
    except ToolError as e:
        raise HTTPException(409, str(e))

    pa.status = "confirmed"
    S.audit(db, c, "ai.confirm", pending_id=pa.id, tool=pa.tool)
    db.commit()

    return {"result": result}


@app.post("/ai/cancel/{pid}")
def ai_cancel(
    pid: int,
    c: Ctx = Depends(need("owner")),
    db: Session = Depends(get_db)
):
    _require_ai()
    pa = _pending(db, c, pid)

    if pa.status != "pending":
        raise HTTPException(409, f"already {pa.status}")

    pa.status = "cancelled"
    S.audit(db, c, "ai.cancel", pending_id=pa.id)
    db.commit()

    return {"ok": True}

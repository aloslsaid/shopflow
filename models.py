from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, String, Integer, Numeric, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase): pass
def pk(): return mapped_column(Integer, primary_key=True)
def tid(): return mapped_column(ForeignKey("store.id"), index=True)  # tenant key on EVERY table

class Store(Base):
    __tablename__ = "store"; id = pk(); name: Mapped[str] = mapped_column(String(120))
    wa_token_enc: Mapped[str | None]; ig_token_enc: Mapped[str | None]
class User(Base):
    __tablename__ = "user"; id = pk(); store_id = tid()
    email: Mapped[str] = mapped_column(String(200), unique=True)
    pw_hash: Mapped[str]; role: Mapped[str] = mapped_column(String(20))  # owner|manager|staff
class Product(Base):
    __tablename__ = "product"; id = pk(); store_id = tid(); name: Mapped[str]
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2)); cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    active: Mapped[bool] = mapped_column(default=True)
class Stock(Base):
    __tablename__ = "stock"; id = pk(); store_id = tid()
    product_id = mapped_column(ForeignKey("product.id")); size: Mapped[str]; color: Mapped[str]
    qty: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (UniqueConstraint("product_id", "size", "color"),)
class Order(Base):
    __tablename__ = "order"; id = pk(); store_id = tid()
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft|approved|rejected|out_for_delivery|delivered|cancelled
    customer_name: Mapped[str]; phone: Mapped[str]; address: Mapped[str]
    agent_phone: Mapped[str | None] = mapped_column(String(30), default=None)
    conversation: Mapped[list] = mapped_column(JSON, default=list)
    items = relationship("OrderItem", cascade="all")
class OrderItem(Base):
    __tablename__ = "order_item"; id = pk(); store_id = tid(); order_id = mapped_column(ForeignKey("order.id"))
    product_id = mapped_column(ForeignKey("product.id")); size: Mapped[str]; color: Mapped[str]
    qty: Mapped[int]; unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))  # snapshotted on delivery
class AuditLog(Base):
    __tablename__ = "audit_log"; id = pk(); store_id = tid(); user_id: Mapped[int | None]
    action: Mapped[str]; detail: Mapped[dict] = mapped_column(JSON); at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Sale(Base):
    __tablename__ = "sale"; id = pk(); store_id = tid(); order_id = mapped_column(ForeignKey("order.id"), unique=True)
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2)); cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    profit: Mapped[Decimal] = mapped_column(Numeric(12, 2)); at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Customer(Base):
    __tablename__ = "customer"; id = pk(); store_id = tid(); name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(30), default=None); address: Mapped[str | None] = mapped_column(String(300), default=None)
class Expense(Base):
    __tablename__ = "expense"; id = pk(); store_id = tid(); title: Mapped[str] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2)); category: Mapped[str | None] = mapped_column(String(60), default=None)
    at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
class PendingAction(Base):
    __tablename__ = "pending_action"; id = pk(); store_id = tid(); user_id: Mapped[int]
    tool: Mapped[str] = mapped_column(String(40)); args: Mapped[dict] = mapped_column(JSON); summary: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(12), default="pending"); created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

"""DB-backed AI workflow tests. Need fastapi+sqlalchemy installed (NOT runnable in the authoring sandbox)."""
import os, json
os.environ.update(JWT_SECRET="t", DATABASE_URL="sqlite:///:memory:")
from fastapi.testclient import TestClient
from app.main import app, get_llm
def H(t): return {"Authorization": f"Bearer {t}"}
def call(name, args): return {"choices": [{"message": {"content": "", "tool_calls": [{"id": "1", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}
class Fake:
    def __init__(s, *r): s.r = list(r)
    def chat(s, m, t=None): return s.r.pop(0)
def say(t): return {"choices": [{"message": {"content": t}}]}
def reg(cl, n): return cl.post("/auth/register-store", json={"store_name": n, "email": f"{n}@x.com", "password": "password1"}).json()["token"]
def chat(cl, tok, llm, msg="go"):
    app.dependency_overrides[get_llm] = lambda: llm
    return cl.post("/ai/chat", json={"message": msg}, headers=H(tok)).json()

def test_ai_stock_price_sale_profit_flow_and_isolation():
    with TestClient(app) as cl:
        a, b = reg(cl, "a2"), reg(cl, "b2")
        chat(cl, a, Fake(call("add_product", {"name": "Black Jacket", "price": 50000, "cost": 30000}), say("added")))
        out = chat(cl, a, Fake(call("adjust_stock", {"product": "jacket", "changes": [{"size": "M", "color": "black", "delta": 10}, {"size": "L", "color": "black", "delta": 10}]}), say("confirm?")))
        pid = out["pending"][0]["id"]
        assert cl.get("/products", headers=H(a)).json()[0]["stock"] == 0          # nothing applied before confirmation
        assert cl.post(f"/ai/confirm/{pid}", headers=H(b)).status_code == 404       # other store cannot confirm
        assert cl.post(f"/ai/confirm/{pid}", headers=H(a)).status_code == 200
        assert cl.post(f"/ai/confirm/{pid}", headers=H(a)).status_code == 409       # no double execution
        assert cl.get("/products", headers=H(a)).json()[0]["stock"] == 20
        out = chat(cl, a, Fake(call("set_price", {"product": "jacket", "price": 40000}), say("confirm?")))
        assert cl.get("/products", headers=H(a)).json()[0]["price"].startswith("50000")
        cl.post(f"/ai/confirm/{out['pending'][0]['id']}", headers=H(a))
        assert cl.get("/products", headers=H(a)).json()[0]["price"].startswith("40000")
        out = chat(cl, a, Fake(call("record_sale", {"items": [{"product": "jacket", "size": "M", "color": "black", "qty": 3}]}), say("confirm?")))
        cl.post(f"/ai/confirm/{out['pending'][0]['id']}", headers=H(a))
        d = cl.get("/dashboard", headers=H(a)).json()
        assert d["total_sales"].startswith("120000") and d["gross_profit"].startswith("30000")   # (40000-30000)*3
        assert cl.get("/products", headers=H(a)).json()[0]["stock"] == 17
        out = chat(cl, a, Fake(call("record_sale", {"items": [{"product": "jacket", "qty": 1}]}), say("which size?")))  # ambiguous variant -> no pending
        assert out["pending"] == []
        assert cl.get("/dashboard", headers=H(b)).json()["total_sales"] == "0"
        cl.post("/expenses", json={"title": "rent", "amount": "10000"}, headers=H(a))
        assert cl.get("/dashboard", headers=H(a)).json()["net_profit"].startswith("20000")

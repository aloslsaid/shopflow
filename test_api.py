import os
os.environ.update(JWT_SECRET="t", DATABASE_URL="sqlite:///:memory:")
from fastapi.testclient import TestClient
from app.main import app
def H(t): return {"Authorization": f"Bearer {t}"}
def reg(cl, n): return cl.post("/auth/register-store", json={"store_name": n, "email": f"{n}@x.com", "password": "password1"}).json()["token"]
def test_full_flow_and_isolation():
    with TestClient(app) as cl:
        a, b = reg(cl, "a"), reg(cl, "b")
        pid = cl.post("/products", json={"name": "Jacket", "price": "50", "cost": "30"}, headers=H(a)).json()["id"]
        cl.post("/stock", json={"product_id": pid, "size": "M", "color": "black", "delta": 10}, headers=H(a))
        o = cl.post("/orders", json={"customer_name": "C", "phone": "+9647701234567", "address": "Baghdad", "items": [{"product_id": pid, "size": "M", "color": "black", "qty": 2}]}, headers=H(a)).json()
        assert cl.get(f"/orders/{o['id']}", headers=H(b)).status_code == 404
        assert cl.post(f"/orders/{o['id']}/approve", headers=H(b)).status_code == 404
        cl.post(f"/orders/{o['id']}/approve", headers=H(a))
        d = cl.post(f"/orders/{o['id']}/dispatch", json={"agent_phone": "+9647709999999"}, headers=H(a)).json()
        assert "wa.me" in d["whatsapp_link"]
        assert cl.post(f"/orders/{o['id']}/deliver", headers=H(a)).status_code == 200
        dash = cl.get("/dashboard", headers=H(a)).json()
        assert dash["total_sales"] == "100.00" and dash["net_profit"] == "40.00"
        assert cl.get("/dashboard", headers=H(b)).json()["total_sales"] == "0"

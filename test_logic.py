import pytest, os
from cryptography.fernet import Fernet
from app.logic import *
def test_profit_uses_actual_cost():
    r, c, p = order_profit([{"qty": 2, "unit_price": 50, "unit_cost": 30}, {"qty": 1, "unit_price": 20, "unit_cost": 5}])
    assert (r, c, p) == (120, 65, 55)
def test_wa_link_and_message():
    o = {"customer_name": "A", "phone": "+964 770", "address": "Baghdad", "total": 120, "items": [{"qty": 2, "name": "Jacket", "size": "M", "color": "black"}]}
    assert "2x Jacket (M/black)" in delivery_message(o, "S")
    assert wa_link("+964 7701234567", "hi x").startswith("https://wa.me/9647701234567?text=hi%20x")
    with pytest.raises(ValueError): wa_link("12", "x")
def test_stock_rejects_negative():
    assert apply_stock({("j", "M"): 10}, {("j", "M"): 5})[("j", "M")] == 15
    with pytest.raises(ValueError): apply_stock({("j", "M"): 1}, {("j", "M"): -2})
def test_crypto_roundtrip():
    os.environ["CREDENTIALS_KEY"] = Fernet.generate_key().decode()
    from app.crypto import encrypt, decrypt
    assert decrypt(encrypt("tok")) == "tok" != encrypt("tok")

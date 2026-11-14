import httpx, logging
log = logging.getLogger("shopflow.whatsapp")
def send_text(token: str, phone_number_id: str, to: str, body: str) -> dict:
    """Real WhatsApp Cloud API call. Needs a store's token + phone_number_id (not available here, so never executed)."""
    r = httpx.post(f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                   headers={"Authorization": f"Bearer {token}"}, timeout=15,
                   json={"messaging_product": "whatsapp", "to": "".join(c for c in to if c.isdigit()), "type": "text", "text": {"body": body}})
    if r.status_code >= 400: log.error("whatsapp send failed %s %s", r.status_code, r.text); r.raise_for_status()
    return r.json()

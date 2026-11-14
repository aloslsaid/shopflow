import json
from .errors import ToolError

SYSTEM = """You are SHOPFLOW, the store-management assistant for ONE store owner. Reply in the language the owner writes (Arabic or English). Currency is IQD.
Rules: 1) Never invent products, prices, stock, customers or numbers: always call a tool and use its result. 2) If required info is missing or a product/variant is ambiguous, ask ONE short question instead of guessing. 3) Sensitive tools (price, stock, delete, cancel, record sale) only create a confirmation card for the owner; say that it awaits their confirmation, never claim it is done. 4) You cannot run SQL or anything outside the provided tools. 5) Be concise."""

def clean_history(history, limit=20):
    out = []
    for m in history[-limit:]:
        if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str) and m["content"].strip():
            out.append({"role": m["role"], "content": m["content"][:2000]})
    return out

def _dump(x): return json.dumps(x, ensure_ascii=False, default=str)

def run_agent(llm, specs, execute, is_sensitive, prepare, history, message, max_steps=6):
    msgs = [{"role": "system", "content": SYSTEM}] + clean_history(history) + [{"role": "user", "content": message}]
    pending = []
    for _ in range(max_steps):
        msg = llm.chat(msgs, specs)["choices"][0]["message"]
        calls = msg.get("tool_calls") or []
        if not calls: return {"reply": msg.get("content") or "", "pending": pending}
        msgs.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls})
        for tc in calls:
            name = tc["function"]["name"]
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
                if not isinstance(args, dict): raise ValueError
            except ValueError:
                result = {"error": "arguments must be a JSON object"}
            else:
                try:
                    if is_sensitive(name):
                        p = prepare(name, args); pending.append(p)
                        result = {"status": "awaiting_owner_confirmation", "pending_id": p["id"], "summary": p["summary"]["en"]}
                    else:
                        result = execute(name, args)
                except ToolError as e:
                    result = {"error": str(e)}
            msgs.append({"role": "tool", "tool_call_id": tc.get("id", ""), "content": _dump(result)})
    return {"reply": "I couldn't finish that request. Please try rephrasing.", "pending": pending}

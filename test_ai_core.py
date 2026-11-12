import json, os, pathlib, pytest
from datetime import datetime
from decimal import Decimal
pytest.importorskip("shopflow.ai.agent", reason="Optional AI integration package is not included in this checkout.")\nfrom shopflow.ai.agent import run_agent, clean_history
from shopflow.ai.errors import ToolError, LLMNotConfigured, LLMError
from shopflow.ai.llm import OpenRouterClient
from shopflow.logic import period_bounds, summarize

def call(name, args, id="c1"): return {"choices": [{"message": {"content": "", "tool_calls": [{"id": id, "function": {"name": name, "arguments": json.dumps(args)}}]}}]}
def say(t): return {"choices": [{"message": {"content": t}}]}
class FakeLLM:
    def __init__(s, *r): s.r, s.seen = list(r), []
    def chat(s, m, t=None): s.seen.append(json.loads(json.dumps(m))); return s.r.pop(0)
SENS = lambda n: n in {"set_price"}

def test_plain_reply():
    assert run_agent(FakeLLM(say("hi")), [], None, SENS, None, [], "hello") == {"reply": "hi", "pending": []}
def test_tool_result_is_fed_back():
    llm = FakeLLM(call("low_stock", {}), say("2 items low"))
    out = run_agent(llm, [], lambda n, a: [{"product": "Jacket", "qty": 1}], SENS, None, [], "low?")
    assert out["reply"] == "2 items low" and "Jacket" in llm.seen[1][-1]["content"]
def test_sensitive_tool_is_never_executed_only_prepared():
    ran = []
    prep = lambda n, a: {"id": 7, "tool": n, "summary": {"en": "Change price", "ar": "x"}}
    out = run_agent(FakeLLM(call("set_price", {"product": "j", "price": 40000}), say("Please confirm")), [], lambda n, a: ran.append(n), SENS, prep, [], "price 40000")
    assert ran == [] and out["pending"][0]["id"] == 7
def test_tool_error_goes_back_to_model_so_it_can_ask():
    def boom(n, a): raise ToolError("ambiguous product 'phone'; candidates: #1 A, #2 B")
    llm = FakeLLM(call("search_products", {"query": "phone"}), say("Which phone?"))
    out = run_agent(llm, [], boom, SENS, None, [], "I sold 3 phones")
    assert out["reply"] == "Which phone?" and "ambiguous" in llm.seen[1][-1]["content"]
def test_bad_json_args_handled_and_loop_is_bounded():
    bad = {"choices": [{"message": {"content": "", "tool_calls": [{"id": "1", "function": {"name": "x", "arguments": "{oops"}}]}}]}
    out = run_agent(FakeLLM(*[bad] * 3), [], None, SENS, None, [], "hi", max_steps=3)
    assert "couldn't finish" in out["reply"]
def test_history_only_keeps_user_and_assistant_text():
    h = [{"role": "system", "content": "evil"}, {"role": "tool", "content": "x"}, {"role": "user", "content": "a"}, {"role": "assistant", "content": 5}]
    assert clean_history(h) == [{"role": "user", "content": "a"}]

def test_llm_client_uses_env_and_builds_request(monkeypatch=None):
    os.environ.update(OPENROUTER_API_KEY="k-test", OPENROUTER_MODEL="m/x", OPENROUTER_BASE_URL="https://example.test/v1/")
    got = {}
    class R: status_code = 200; json = lambda s: {"ok": 1}
    def post(url, headers, json, timeout): got.update(url=url, h=headers, b=json); return R()
    assert OpenRouterClient(post).chat([{"role": "user", "content": "x"}], [{"t": 1}]) == {"ok": 1}
    assert got["url"] == "https://example.test/v1/chat/completions" and got["h"]["Authorization"] == "Bearer k-test"
    assert got["b"]["model"] == "m/x" and got["b"]["tools"] == [{"t": 1}]
def test_llm_client_errors():
    os.environ.pop("OPENROUTER_API_KEY", None)
    with pytest.raises(LLMNotConfigured): OpenRouterClient(lambda **k: None).chat([])
    os.environ["OPENROUTER_API_KEY"] = "k"
    class R: status_code = 429
    with pytest.raises(LLMError): OpenRouterClient(lambda *a, **k: R()).chat([])
def test_no_api_key_hardcoded_in_source():
    for f in pathlib.Path("shopflow/ai").rglob("*.py"): assert "sk-or" not in f.read_text(), f

def test_period_bounds_baghdad():
    now = datetime(2026, 11, 8, 22, 30)  # 01:30 on Nov 9 in Baghdad
    assert period_bounds("today", now)[0] == datetime(2026, 11, 8, 21, 0)
    assert period_bounds("week", now)[0] == datetime(2026, 11, 2, 21, 0)
    assert period_bounds("month", now)[0] == datetime(2026, 10, 31, 21, 0)
    assert period_bounds("all", now)[0] is None
    with pytest.raises(ValueError): period_bounds("year", now)
def test_summarize_net_profit_subtracts_expenses():
    r = summarize([("100.00", "60.00"), (50, 20)], ["10"])
    assert (r["revenue"], r["cost"], r["gross_profit"], r["expenses"], r["net_profit"], r["sales_count"]) == (150, 80, 70, 10, 60, 2)

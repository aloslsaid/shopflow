
import { useCallback, useEffect, useState } from "react";
import { api, login } from "./api";
import { Lang, t } from "./i18n";
import Chat from "./Chat";

type Tab = "dashboard" | "products" | "orders" | "delivery" | "customers" | "expenses" | "analytics";
const TABS: Tab[] = ["dashboard", "products", "orders", "delivery", "customers", "expenses", "analytics"];

const Card = ({ k, v }: { k: string; v: any }) => (
  <div className="bg-white p-4 rounded-xl shadow">
    <div className="text-xs text-slate-500">{k}</div>
    <div className="text-xl font-semibold">{v}</div>
  </div>
);

const Table = ({ head, rows }: { head: string[]; rows: any[][] }) => (
  <div className="bg-white rounded-xl shadow overflow-x-auto">
    <table className="w-full text-start text-sm">
      <thead><tr>{head.map(h => <th key={h} className="p-2 text-start text-slate-500">{h}</th>)}</tr></thead>
      <tbody>{rows.map((r, i) => (
        <tr key={i} className="border-t">
          {r.map((c, j) => <td key={j} className="p-2">{c}</td>)}
        </tr>
      ))}</tbody>
    </table>
  </div>
);

export default function App() {
  const [token, setToken] = useState(localStorage.getItem("t") ?? "");
  const [lang, setLang] = useState<Lang>((localStorage.getItem("lang") as Lang) ?? "ar");
  const [tab, setTab] = useState<Tab>("dashboard");
  const [chatOpen, setChatOpen] = useState(false);
  const [err, setErr] = useState("");
  const [d, setD] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [orders, setOrders] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [expenses, setExpenses] = useState<any[]>([]);
  const [period, setPeriod] = useState("today");
  const [rep, setRep] = useState<any>(null);
  const [form, setForm] = useState({ title: "", amount: "" });

  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [storeName, setStoreName] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authLoading, setAuthLoading] = useState(false);

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
    localStorage.setItem("lang", lang);
  }, [lang]);

  const load = useCallback(() => {
    if (!token) return;
    Promise.all([
      api("/dashboard", token),
      api("/products", token),
      api("/orders", token),
      api("/customers", token),
      api("/expenses", token),
      api("/reports?period=" + period, token)
    ]).then(([a, b, c, e, f, g]) => {
      setD(a);
      setProducts(b);
      setOrders(c);
      setCustomers(e);
      setExpenses(f);
      setRep(g);
      setErr("");
    }).catch(x => setErr(x.message));
  }, [token, period]);

  useEffect(load, [load]);

  const act = (id: number, a: string, body?: unknown) =>
    api(`/orders/${id}/${a}`, token, "POST", body)
      .then(r => {
        if (r.whatsapp_link) window.open(r.whatsapp_link);
        load();
      })
      .catch(x => setErr(x.message));

  const submitAuth = async () => {
    setErr("");

    if (!email.trim() || !pw) {
      setErr("يرجى إدخال البريد الإلكتروني وكلمة المرور");
      return;
    }

    if (authMode === "register" && !storeName.trim()) {
      setErr("يرجى إدخال اسم المتجر");
      return;
    }

    try {
      setAuthLoading(true);

      if (authMode === "register") {
        const response = await api("/auth/register-store", "", "POST", {
          store_name: storeName.trim(),
          email: email.trim(),
          password: pw
        });

        // بعض الباك إندات تسجل الدخول تلقائياً بعد التسجيل.
        const newToken = response.token || response.access_token;

        if (newToken) {
          localStorage.setItem("t", newToken);
          setToken(newToken);
        } else {
          // إذا التسجيل لا يعيد token، ننتقل إلى تسجيل الدخول.
          setAuthMode("login");
          setPw("");
          setErr("تم إنشاء الحساب بنجاح. سجّل الدخول الآن.");
        }
      } else {
        const newToken = await login(email.trim(), pw);
        localStorage.setItem("t", newToken);
        setToken(newToken);
      }
    } catch (x: any) {
      setErr(x.message || "حدث خطأ أثناء تنفيذ الطلب");
    } finally {
      setAuthLoading(false);
    }
  };

  const OrderList = ({ list }: { list: any[] }) => (
    <div className="space-y-3">
      {list.map(o => (
        <div key={o.id} className="bg-white p-4 rounded-xl shadow">
          <div className="flex justify-between">
            <b>#{o.id} {o.customer_name}</b>
            <span className="text-sm">{o.status}</span>
          </div>
          <div className="text-sm text-slate-600">{o.phone} · {o.address}</div>
          <div className="flex gap-2 mt-2 flex-wrap">
            {o.status === "draft" && <>
              <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={() => act(o.id, "approve")}>{t(lang, "approve")}</button>
              <button className="px-3 py-1 bg-red-600 text-white rounded" onClick={() => act(o.id, "reject")}>{t(lang, "reject")}</button>
            </>}
            {o.status === "approved" && (
              <button className="px-3 py-1 bg-indigo-600 text-white rounded" onClick={() => {
                const p = prompt(t(lang, "agentPhone"));
                if (p) act(o.id, "dispatch", { agent_phone: p });
              }}>{t(lang, "dispatch")}</button>
            )}
            {o.status === "out_for_delivery" && (
              <button className="px-3 py-1 bg-emerald-600 text-white rounded" onClick={() => act(o.id, "deliver")}>{t(lang, "done")}</button>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  if (!token) {
    return (
      <div className="max-w-sm mx-auto mt-16 p-6 bg-white rounded-xl shadow space-y-4">
        <h1 className="text-2xl font-bold text-center">SHOPFLOW AI</h1>

        <div className="flex rounded-lg bg-slate-100 p-1 gap-1">
          <button
            className={`flex-1 p-2 rounded ${authMode === "login" ? "bg-indigo-600 text-white" : ""}`}
            onClick={() => { setAuthMode("login"); setErr(""); }}
          >
            تسجيل الدخول
          </button>
          <button
            className={`flex-1 p-2 rounded ${authMode === "register" ? "bg-indigo-600 text-white" : ""}`}
            onClick={() => { setAuthMode("register"); setErr(""); }}
          >
            إنشاء حساب
          </button>
        </div>

        {authMode === "register" && (
          <input
            className="border w-full p-3 rounded-lg"
            placeholder="اسم المتجر"
            value={storeName}
            onChange={e => setStoreName(e.target.value)}
          />
        )}

        <input
          className="border w-full p-3 rounded-lg"
          type="email"
          placeholder={t(lang, "email")}
          value={email}
          onChange={e => setEmail(e.target.value)}
        />

        <input
          className="border w-full p-3 rounded-lg"
          type="password"
          placeholder={t(lang, "password")}
          value={pw}
          onChange={e => setPw(e.target.value)}
        />

        <button
          disabled={authLoading}
          className="bg-indigo-600 disabled:opacity-50 text-white w-full p-3 rounded-lg font-semibold"
          onClick={submitAuth}
        >
          {authLoading ? "يرجى الانتظار..." : authMode === "login" ? t(lang, "signin") : "إنشاء حساب المتجر"}
        </button>

        {err && <p className="text-red-600 text-sm text-center">{err}</p>}

        <div className="text-center">
          <button className="text-sm text-slate-500 underline" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            {lang === "ar" ? "English" : "العربية"}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex">
      <nav className="w-44 shrink-0 bg-slate-900 text-white p-3 space-y-1 hidden md:block">
        <div className="font-bold mb-3">SHOPFLOW AI</div>
        {TABS.map(x => (
          <button key={x} onClick={() => setTab(x)} className={`block w-full text-start px-3 py-2 rounded ${tab === x ? "bg-indigo-600" : "hover:bg-slate-800"}`}>
            {t(lang, x)}
          </button>
        ))}
        <button className="block w-full text-start px-3 py-2 text-slate-300" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
          {lang === "ar" ? "English" : "العربية"}
        </button>
        <button className="block w-full text-start px-3 py-2 text-slate-300" onClick={() => {
          localStorage.removeItem("t");
          setToken("");
        }}>
          {t(lang, "logout")}
        </button>
      </nav>

      <main className="flex-1 p-4 space-y-4 min-w-0">
        <div className="md:hidden flex gap-1 overflow-x-auto">
          {TABS.map(x => (
            <button key={x} onClick={() => setTab(x)} className={`px-3 py-1 rounded whitespace-nowrap ${tab === x ? "bg-indigo-600 text-white" : "bg-white"}`}>
              {t(lang, x)}
            </button>
          ))}
          <button className="px-3 py-1 bg-white rounded" onClick={() => setLang(lang === "ar" ? "en" : "ar")}>
            {lang === "ar" ? "EN" : "ع"}
          </button>
        </div>

        {err && <p className="text-red-600">{err}</p>}

        {tab === "dashboard" && d && <>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Card k={t(lang, "sales")} v={d.total_sales} />
            <Card k={t(lang, "gross")} v={d.gross_profit} />
            <Card k={t(lang, "exp")} v={d.expenses} />
            <Card k={t(lang, "net")} v={d.net_profit} />
            <Card k={t(lang, "pending")} v={d.orders_by_status.draft ?? 0} />
            <Card k={t(lang, "delivered")} v={d.orders_by_status.delivered ?? 0} />
          </div>
          <h3 className="font-semibold">{t(lang, "low")}</h3>
          <Table head={["#", "", "", t(lang, "stock")]} rows={d.low_stock.map((x: any) => [x.product_id, x.size, x.color, x.qty])} />
        </>}

        {tab === "products" && <Table head={[t(lang, "name"), t(lang, "price"), t(lang, "cost"), t(lang, "stock")]} rows={products.map(p => [p.name, p.price, p.cost, p.stock])} />}
        {tab === "orders" && <OrderList list={orders} />}
        {tab === "delivery" && <OrderList list={orders.filter(o => ["approved", "out_for_delivery"].includes(o.status))} />}
        {tab === "customers" && <Table head={[t(lang, "name"), t(lang, "phone"), t(lang, "address")]} rows={customers.map(c => [c.name, c.phone, c.address])} />}

        {tab === "expenses" && <>
          <div className="flex gap-2">
            <input className="border rounded p-2 flex-1" placeholder={t(lang, "title")} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} />
            <input className="border rounded p-2 w-32" inputMode="decimal" placeholder={t(lang, "amount")} value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} />
            <button className="px-4 bg-indigo-600 text-white rounded" onClick={() => api("/expenses", token, "POST", form).then(() => {
              setForm({ title: "", amount: "" });
              load();
            }).catch(x => setErr(x.message))}>{t(lang, "add")}</button>
          </div>
          <Table head={[t(lang, "title"), t(lang, "amount")]} rows={expenses.map(e => [e.title, e.amount])} />
        </>}

        {tab === "analytics" && rep && <>
          <div className="flex gap-2">
            {["today", "week", "month", "all"].map(p => (
              <button key={p} onClick={() => setPeriod(p)} className={`px-3 py-1 rounded ${period === p ? "bg-indigo-600 text-white" : "bg-white"}`}>
                {t(lang, p as any)}
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <Card k={t(lang, "sales")} v={rep.revenue} />
            <Card k={t(lang, "cost2")} v={rep.cost} />
            <Card k={t(lang, "gross")} v={rep.gross_profit} />
            <Card k={t(lang, "net")} v={rep.net_profit} />
          </div>
        </>}
      </main>

      <aside className={`${chatOpen ? "fixed inset-0 z-20" : "hidden"} md:static md:block md:w-96 md:shrink-0 border-s`}>
        <div className="h-screen md:sticky md:top-0 relative">
          <button className="md:hidden absolute top-2 end-2 z-30 text-xl" onClick={() => setChatOpen(false)}>✕</button>
          <Chat token={token} lang={lang} onChange={load} />
        </div>
      </aside>

      {!chatOpen && <button className="md:hidden fixed bottom-4 end-4 z-10 w-14 h-14 rounded-full bg-indigo-600 text-white shadow-lg" onClick={() => setChatOpen(true)}>AI</button>}
    </div>
  );
}

import { useEffect, useRef, useState } from "react";
import { api } from "./api"; import { Lang, t } from "./i18n";
type Pending = { id: number; summary: { en: string; ar: string }; state?: "done" | "cancelled" };
type Msg = { role: "user" | "assistant"; content: string; pending?: Pending[] };
export default function Chat({ token, lang, onChange }: { token: string; lang: Lang; onChange: () => void }) {
  const [msgs, setMsgs] = useState<Msg[]>(() => JSON.parse(localStorage.getItem("chat") ?? "[]"));
  const [text, setText] = useState(""); const [busy, setBusy] = useState(false); const end = useRef<HTMLDivElement>(null);
  useEffect(() => { localStorage.setItem("chat", JSON.stringify(msgs.slice(-60))); end.current?.scrollIntoView(); }, [msgs]);
  const send = async () => {
    const m = text.trim(); if (!m || busy) return; setText(""); setBusy(true);
    const history = msgs.map(({ role, content }) => ({ role, content }));
    setMsgs(x => [...x, { role: "user", content: m }]);
    try { const r = await api("/ai/chat", token, "POST", { message: m, history }); setMsgs(x => [...x, { role: "assistant", content: r.reply, pending: r.pending }]); onChange(); }
    catch (e: any) { setMsgs(x => [...x, { role: "assistant", content: "⚠ " + e.message }]); }
    setBusy(false);
  };
  const decide = async (mi: number, p: Pending, ok: boolean) => {
    try { await api(`/ai/${ok ? "confirm" : "cancel"}/${p.id}`, token, "POST"); onChange(); setMsgs(x => x.map((m, i) => i !== mi ? m : { ...m, pending: m.pending?.map(q => q.id === p.id ? { ...q, state: ok ? "done" : "cancelled" } : q) })); }
    catch (e: any) { setMsgs(x => [...x, { role: "assistant", content: "⚠ " + e.message }]); }
  };
  return (<div className="flex flex-col h-full bg-white">
    <div className="p-3 border-b font-semibold">{t(lang, "aiTitle")}</div>
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {msgs.map((m, i) => (<div key={i} className={m.role === "user" ? "text-end" : "text-start"}>
        <div dir="auto" className={`inline-block max-w-[90%] px-3 py-2 rounded-2xl whitespace-pre-wrap ${m.role === "user" ? "bg-indigo-600 text-white" : "bg-slate-100"}`}>{m.content}</div>
        {m.pending?.map(p => (<div key={p.id} className="mt-2 border-2 border-amber-400 bg-amber-50 rounded-xl p-3 text-start">
          <div dir="auto" className="text-sm font-medium">{p.summary[lang]}</div>
          {p.state ? <div className="text-xs mt-1">{p.state === "done" ? "✓" : "✕"}</div> :
            <div className="flex gap-2 mt-2"><button className="px-3 py-1 rounded bg-green-600 text-white" onClick={() => decide(i, p, true)}>{t(lang, "confirm")}</button><button className="px-3 py-1 rounded bg-slate-300" onClick={() => decide(i, p, false)}>{t(lang, "cancel")}</button></div>}
        </div>))}
      </div>))}
      {busy && <div className="text-slate-400">…</div>}<div ref={end} />
    </div>
    <div className="p-3 border-t flex gap-2">
      <input dir="auto" className="flex-1 border rounded-lg px-3 py-2" placeholder={t(lang, "aiHint")} value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} />
      <button className="px-4 rounded-lg bg-indigo-600 text-white disabled:opacity-50" disabled={busy} onClick={send}>{t(lang, "send")}</button>
    </div></div>);
}

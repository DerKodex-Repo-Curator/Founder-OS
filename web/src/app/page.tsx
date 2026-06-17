"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function kv(label: string, value: string | number | boolean) {
  return (
    <div className="kv">
      <span className="muted">{label}</span>
      <span className="v">{String(value)}</span>
    </div>
  );
}

export default function OverviewPage() {
  const [state, setState] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.getState().then(setState).catch((e) => setError(e.message));
    const t = setInterval(() => api.getState().then(setState).catch(() => {}), 15000);
    return () => clearInterval(t);
  }, []);

  if (error) return <div className="error">Failed to load: {error}. Is the API running on :8788?</div>;
  if (!state) return <div className="muted">Loading...</div>;

  const about = state.about || {};
  const snap = state.snapshot || {};
  const usage = state.usage || {};
  const fin = state.finance || {};
  const crm = snap.crm || {};

  return (
    <>
      <h1 className="page-title">Overview</h1>
      <div className="grid">
        <div className="card">
          <h2>Agent</h2>
          {kv("Name", about.name || "Founder OS")}
          {kv("Tools", about.total_tools || "?")}
          {kv("Categories", Object.keys(about.tools_by_category || {}).length)}
          <div className="muted" style={{ marginTop: 8, fontSize: 13 }}>{about.tagline}</div>
        </div>

        <div className="card">
          <h2>Business snapshot</h2>
          {kv("Contacts", crm.total_contacts || 0)}
          {kv("Follow-ups due", crm.followups_due || 0)}
          {kv("Open tasks", snap.tasks_open || 0)}
          {kv("Active goals", (snap.goals_active || []).length)}
          {kv("Pending approvals", snap.approvals_pending || 0)}
        </div>

        <div className="card">
          <h2>Today&apos;s usage</h2>
          {kv("LLM calls", usage.llm_calls || 0)}
          {kv("Est. cost", `$${usage.est_cost_usd || 0}`)}
          {kv("Autonomy", usage.autonomy_level || "?")}
          {kv("Paused", usage.paused || false)}
        </div>

        {fin.set && (
          <div className="card">
            <h2>Runway</h2>
            {kv("Cash", `$${(fin.cash || 0).toLocaleString()}`)}
            {kv("Monthly burn", `$${(fin.monthly_burn || 0).toLocaleString()}`)}
            {kv("MRR", `$${(fin.mrr || 0).toLocaleString()}`)}
            {kv("Runway", fin.runway || `${fin.runway_months} months`)}
          </div>
        )}

        <div className="card">
          <h2>Active goals</h2>
          <ul style={{ paddingLeft: 18, fontSize: 13 }}>
            {(state.goals || []).slice(0, 8).map((g: any) => (
              <li key={g.id}>{g.title}</li>
            ))}
            {!(state.goals || []).length && <li className="muted">No active goals.</li>}
          </ul>
        </div>

        <div className="card">
          <h2>Pending approvals</h2>
          {(state.approvals || []).slice(0, 6).map((a: any) => (
            <div key={a.id} style={{ fontSize: 13, padding: "6px 0", borderBottom: "1px solid #18224a" }}>
              <span className="muted">#{a.id}</span> {(a.summary || "").slice(0, 100)}
            </div>
          ))}
          {!(state.approvals || []).length && <div className="muted">Nothing waiting.</div>}
        </div>

        <div className="card">
          <h2>Recent turns</h2>
          {(state.traces || []).slice(0, 6).map((t: any, i: number) => (
            <div key={i} style={{ fontSize: 13, padding: "6px 0", borderBottom: "1px solid #18224a" }}>
              <span className="muted">{t.actor}</span> {(t.message || "").slice(0, 70)}
            </div>
          ))}
        </div>
      </div>
    </>
  );
}

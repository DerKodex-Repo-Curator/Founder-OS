"use client";

import { useEffect, useState } from "react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8788";

function kv(label: string, value: string | number) {
  return (
    <div className="kv">
      <span className="muted">{label}</span>
      <span className="v">{String(value)}</span>
    </div>
  );
}

export default function CognitionPage() {
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${BASE}/api/cognition`)
      .then((r) => r.json())
      .then(setData)
      .catch((e) => setError(e.message));
    const t = setInterval(
      () => fetch(`${BASE}/api/cognition`).then((r) => r.json()).then(setData).catch(() => {}),
      20000,
    );
    return () => clearInterval(t);
  }, []);

  if (error) return <div className="error">Failed: {error}</div>;
  if (!data) return <div className="muted">Loading cognition panel...</div>;

  const m = data.metrics || {};
  const pre = m.preplay || {};
  const pr = m.principles || {};
  const tr = m.trust || {};

  return (
    <>
      <h1 className="page-title">Cognition (LECE)</h1>
      <div className="grid">
        <div className="card">
          <h2>Preplay accuracy</h2>
          {kv("Runs", pre.count || 0)}
          {kv("MAE", pre.mae ?? 0)}
          {kv("Accuracy", `${((pre.accuracy || 0) * 100).toFixed(0)}%`)}
        </div>
        <div className="card">
          <h2>Principles</h2>
          {kv("Active", pr.count || 0)}
          {kv("Avg effectiveness", pr.avg_effectiveness ?? 0)}
          {kv("Quarantined", pr.quarantined || 0)}
        </div>
        <div className="card">
          <h2>Trust scores</h2>
          {kv("Action types", tr.count || 0)}
          {kv("Avg competence", tr.avg_competence ?? 0)}
        </div>
        <div className="card">
          <h2>Workspace</h2>
          {kv("Active items", data.workspace?.active_items || 0)}
          <ul style={{ paddingLeft: 18, fontSize: 13 }}>
            {(data.workspace?.items || []).slice(0, 6).map((i: any, idx: number) => (
              <li key={idx}>[{i.source}] {i.content?.slice(0, 80)}</li>
            ))}
          </ul>
        </div>
        <div className="card">
          <h2>Learned principles</h2>
          <ul style={{ paddingLeft: 18, fontSize: 13 }}>
            {(data.principles || []).slice(0, 8).map((p: any) => (
              <li key={p.id}>({(p.effectiveness * 100).toFixed(0)}%) {p.principle?.slice(0, 100)}</li>
            ))}
            {!(data.principles || []).length && <li className="muted">No principles yet.</li>}
          </ul>
        </div>
        <div className="card">
          <h2>Distillation runs</h2>
          <ul style={{ paddingLeft: 18, fontSize: 13 }}>
            {(data.distillation || []).slice(0, 5).map((d: any) => (
              <li key={d.id}>#{d.id} +{d.principles_added} / ~{d.principles_updated} ({d.status})</li>
            ))}
          </ul>
        </div>
      </div>
    </>
  );
}

"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Space } from "@/lib/api";

export default function SpacesPage() {
  const [spaces, setSpaces] = useState<Space[]>([]);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState("");
  const [showForm, setShowForm] = useState(false);

  const load = () => api.listSpaces().then((r) => setSpaces(r.spaces)).catch((e) => setError(e.message));

  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!name.trim()) return;
    try {
      await api.createSpace(name.trim(), description.trim());
      setName("");
      setDescription("");
      setShowForm(false);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (id: number, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!confirm("Delete this context space and all its assets?")) return;
    await api.deleteSpace(id);
    load();
  };

  return (
    <>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Context Spaces</h1>
        <button className="btn" onClick={() => setShowForm(true)}>+ New Space</button>
      </div>

      <p className="muted" style={{ marginBottom: 20, fontSize: 14 }}>
        Named knowledge buckets. Upload files, links, notes, audio, video — the agent uses these when you mention the space (e.g. &quot;regarding Stamped&quot;).
      </p>

      {error && <div className="error">{error}</div>}

      {showForm && (
        <div className="modal-backdrop" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 style={{ marginBottom: 16 }}>Create Context Space</h2>
            <div className="form-row">
              <label>Name</label>
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Stamped" />
            </div>
            <div className="form-row">
              <label>Description</label>
              <textarea value={description} onChange={(e) => setDescription(e.target.value)} placeholder="What is this project about?" />
            </div>
            <div className="actions">
              <button className="btn" onClick={create}>Create</button>
              <button className="btn secondary" onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="space-grid">
        {spaces.map((s) => (
          <Link key={s.id} href={`/spaces/${s.id}`} className="card space-card">
            <h2>{s.name}</h2>
            <p className="muted" style={{ fontSize: 13, marginBottom: 8 }}>
              {(s.description || "No description").slice(0, 120)}
            </p>
            <div style={{ display: "flex", gap: 12, fontSize: 12, color: "var(--muted)" }}>
              <span>{s.asset_count || 0} assets</span>
              <span>{s.alias_count || 0} aliases</span>
            </div>
            <div className="actions">
              <button className="btn sm danger" onClick={(e) => remove(s.id, e)}>Delete</button>
            </div>
          </Link>
        ))}
        {!spaces.length && (
          <div className="card">
            <p className="muted">No context spaces yet. Create one to start adding knowledge.</p>
          </div>
        )}
      </div>
    </>
  );
}

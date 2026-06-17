"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, Asset, SpaceDetail } from "@/lib/api";

function statusPill(status: string) {
  const cls = status === "ready" ? "ok" : status === "failed" ? "crit" : status === "processing" ? "warn" : "pending";
  return <span className={`pill ${cls}`}>{status}</span>;
}

export default function SpaceDetailPage() {
  const params = useParams();
  const router = useRouter();
  const spaceId = Number(params.id);
  const [detail, setDetail] = useState<SpaceDetail | null>(null);
  const [error, setError] = useState("");
  const [linkUrl, setLinkUrl] = useState("");
  const [linkTitle, setLinkTitle] = useState("");
  const [noteText, setNoteText] = useState("");
  const [noteTitle, setNoteTitle] = useState("");
  const [newAlias, setNewAlias] = useState("");
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [preview, setPreview] = useState<Asset | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);

  const load = useCallback(() => {
    api.getSpace(spaceId)
      .then((d) => {
        setDetail(d);
        setEditName(d.space.name);
        setEditDesc(d.space.description || "");
      })
      .catch((e) => setError(e.message));
  }, [spaceId]);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  const uploadFiles = async (files: FileList | File[]) => {
    for (const file of Array.from(files)) {
      await api.uploadAsset(spaceId, file);
    }
    load();
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files.length) uploadFiles(e.dataTransfer.files);
  };

  const saveSpace = async () => {
    await api.updateSpace(spaceId, { name: editName, description: editDesc });
    load();
  };

  const addLink = async () => {
    if (!linkUrl.trim()) return;
    await api.addLink(spaceId, linkUrl.trim(), linkTitle.trim());
    setLinkUrl("");
    setLinkTitle("");
    load();
  };

  const addNote = async () => {
    if (!noteText.trim()) return;
    await api.addNote(spaceId, noteText.trim(), noteTitle.trim());
    setNoteText("");
    setNoteTitle("");
    load();
  };

  const addAlias = async () => {
    if (!newAlias.trim()) return;
    await api.addAlias(spaceId, newAlias.trim());
    setNewAlias("");
    load();
  };

  if (error) return <div className="error">{error}</div>;
  if (!detail) return <div className="muted">Loading...</div>;

  return (
    <>
      <button className="btn secondary sm" onClick={() => router.push("/spaces")} style={{ marginBottom: 12 }}>
        &larr; Back
      </button>

      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Space settings</h2>
        <div className="form-row">
          <label>Name</label>
          <input value={editName} onChange={(e) => setEditName(e.target.value)} />
        </div>
        <div className="form-row">
          <label>Description</label>
          <textarea value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
        </div>
        <button className="btn" onClick={saveSpace}>Save</button>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h2>Aliases</h2>
        <p className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
          Extra trigger phrases so the agent knows which space you mean (e.g. &quot;stamped app&quot;).
        </p>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
          {detail.aliases.map((a) => (
            <span key={a.id} className="pill pending" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              {a.alias}
              <button
                className="btn sm danger"
                style={{ padding: "0 6px", fontSize: 10 }}
                onClick={() => api.deleteAlias(a.id).then(load)}
              >
                x
              </button>
            </span>
          ))}
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <input value={newAlias} onChange={(e) => setNewAlias(e.target.value)} placeholder="Add alias..." style={{ margin: 0 }} />
          <button className="btn" onClick={addAlias}>Add</button>
        </div>
      </div>

      <div
        className={`dropzone ${dragging ? "dragover" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => fileRef.current?.click()}
      >
        Drop files here or click to upload
        <br />
        <span style={{ fontSize: 12 }}>PDF, DOCX, MD, audio, video, images, and more</span>
        <input
          ref={fileRef}
          type="file"
          multiple
          hidden
          onChange={(e) => e.target.files && uploadFiles(e.target.files)}
        />
      </div>

      <div className="grid" style={{ marginBottom: 16 }}>
        <div className="card">
          <h2>Add link</h2>
          <input value={linkUrl} onChange={(e) => setLinkUrl(e.target.value)} placeholder="https://..." />
          <input value={linkTitle} onChange={(e) => setLinkTitle(e.target.value)} placeholder="Title (optional)" />
          <button className="btn" onClick={addLink}>Scrape &amp; save</button>
        </div>
        <div className="card">
          <h2>Add note</h2>
          <input value={noteTitle} onChange={(e) => setNoteTitle(e.target.value)} placeholder="Title (optional)" />
          <textarea value={noteText} onChange={(e) => setNoteText(e.target.value)} placeholder="Write context the agent should know..." />
          <button className="btn" onClick={addNote}>Save note</button>
        </div>
      </div>

      <div className="card">
        <h2>Assets ({detail.assets.length})</h2>
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Kind</th>
              <th>Status</th>
              <th>Chunks</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {detail.assets.map((a) => (
              <tr key={a.id}>
                <td>
                  {a.title || a.url || `Asset #${a.id}`}
                  {a.error && <div className="error" style={{ fontSize: 11 }}>{a.error}</div>}
                </td>
                <td>{a.kind}</td>
                <td>{statusPill(a.status)}</td>
                <td>{a.chunk_count || 0}</td>
                <td>
                  <div className="actions" style={{ margin: 0 }}>
                    <button className="btn sm secondary" onClick={() => setPreview(a)}>View</button>
                    <button className="btn sm secondary" onClick={() => api.reingestAsset(a.id).then(load)}>Re-ingest</button>
                    <button className="btn sm danger" onClick={() => api.deleteAsset(a.id).then(load)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
            {!detail.assets.length && (
              <tr><td colSpan={5} className="muted">No assets yet.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {preview && (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2>{preview.title || preview.url || `Asset #${preview.id}`}</h2>
            <p className="muted">{preview.kind} · {preview.status} · {preview.text_chars || 0} chars</p>
            {preview.url && <p><a href={preview.url} target="_blank" rel="noreferrer">{preview.url}</a></p>}
            <div className="asset-preview">{(preview.extracted_text || "No extracted text yet.").slice(0, 8000)}</div>
            <button className="btn secondary" onClick={() => setPreview(null)} style={{ marginTop: 12 }}>Close</button>
          </div>
        </div>
      )}
    </>
  );
}

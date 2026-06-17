const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8788";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      ...(options?.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  getState: () => request<any>("/api/state"),

  listSpaces: () => request<{ spaces: Space[] }>("/api/spaces"),
  createSpace: (name: string, description: string) =>
    request<Space>("/api/spaces", { method: "POST", body: JSON.stringify({ name, description }) }),
  getSpace: (id: number) => request<SpaceDetail>(`/api/spaces/${id}`),
  updateSpace: (id: number, data: { name?: string; description?: string }) =>
    request<Space>(`/api/spaces/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSpace: (id: number) => request(`/api/spaces/${id}`, { method: "DELETE" }),
  addAlias: (spaceId: number, alias: string) =>
    request<Alias>(`/api/spaces/${spaceId}/aliases`, { method: "POST", body: JSON.stringify({ alias }) }),
  deleteAlias: (aliasId: number) => request(`/api/aliases/${aliasId}`, { method: "DELETE" }),

  uploadAsset: (spaceId: number, file: File, title?: string) => {
    const fd = new FormData();
    fd.append("file", file);
    if (title) fd.append("title", title);
    return request<Asset>(`/api/spaces/${spaceId}/assets`, { method: "POST", body: fd });
  },
  addLink: (spaceId: number, url: string, title?: string) =>
    request<Asset>(`/api/spaces/${spaceId}/links`, { method: "POST", body: JSON.stringify({ url, title }) }),
  addNote: (spaceId: number, text: string, title?: string) =>
    request<Asset>(`/api/spaces/${spaceId}/notes`, { method: "POST", body: JSON.stringify({ text, title }) }),
  deleteAsset: (id: number) => request(`/api/assets/${id}`, { method: "DELETE" }),
  reingestAsset: (id: number) => request(`/api/assets/${id}/reingest`, { method: "POST" }),

  // Phase 2 CRUD
  listContacts: () => request<{ contacts: Contact[] }>("/api/contacts"),
  createContact: (data: Partial<Contact>) =>
    request<Contact>("/api/contacts", { method: "POST", body: JSON.stringify(data) }),
  updateContact: (id: number, data: Partial<Contact>) =>
    request<Contact>(`/api/contacts/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteContact: (id: number) => request(`/api/contacts/${id}`, { method: "DELETE" }),

  listCompanies: () => request<{ companies: Company[] }>("/api/companies"),
  createCompany: (data: Partial<Company>) =>
    request<Company>("/api/companies", { method: "POST", body: JSON.stringify(data) }),
  updateCompany: (id: number, data: Partial<Company>) =>
    request<Company>(`/api/companies/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteCompany: (id: number) => request(`/api/companies/${id}`, { method: "DELETE" }),

  listTasks: () => request<{ tasks: Task[] }>("/api/tasks"),
  createTask: (data: Partial<Task>) =>
    request<Task>("/api/tasks", { method: "POST", body: JSON.stringify(data) }),
  updateTask: (id: number, data: Partial<Task>) =>
    request<Task>(`/api/tasks/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteTask: (id: number) => request(`/api/tasks/${id}`, { method: "DELETE" }),

  listGoals: () => request<{ goals: Goal[] }>("/api/goals"),
  createGoal: (data: Partial<Goal>) =>
    request<Goal>("/api/goals", { method: "POST", body: JSON.stringify(data) }),
  updateGoal: (id: number, data: Partial<Goal>) =>
    request<Goal>(`/api/goals/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteGoal: (id: number) => request(`/api/goals/${id}`, { method: "DELETE" }),

  listReminders: () => request<{ reminders: Reminder[] }>("/api/reminders"),
  createReminder: (data: Partial<Reminder>) =>
    request<Reminder>("/api/reminders", { method: "POST", body: JSON.stringify(data) }),
  updateReminder: (id: number, data: Partial<Reminder>) =>
    request<Reminder>(`/api/reminders/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteReminder: (id: number) => request(`/api/reminders/${id}`, { method: "DELETE" }),

  listLessons: () => request<{ lessons: Lesson[] }>("/api/lessons"),
  createLesson: (data: Partial<Lesson>) =>
    request<Lesson>("/api/lessons", { method: "POST", body: JSON.stringify(data) }),
  updateLesson: (id: number, data: Partial<Lesson>) =>
    request<Lesson>(`/api/lessons/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteLesson: (id: number) => request(`/api/lessons/${id}`, { method: "DELETE" }),

  listSkills: () => request<{ skills: Skill[] }>("/api/skills"),
  createSkill: (data: Partial<Skill>) =>
    request<Skill>("/api/skills", { method: "POST", body: JSON.stringify(data) }),
  updateSkill: (id: number, data: Partial<Skill>) =>
    request<Skill>(`/api/skills/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
  deleteSkill: (id: number) => request(`/api/skills/${id}`, { method: "DELETE" }),

  listApprovals: () => request<{ approvals: Approval[] }>("/api/approvals"),
  approveAction: (id: number) => request(`/api/approvals/${id}/approve`, { method: "POST" }),
  rejectAction: (id: number) => request(`/api/approvals/${id}/reject`, { method: "POST" }),

  getFinance: () => request<any>("/api/finance"),
  setFinance: (data: { cash: number; monthly_burn: number; mrr?: number; note?: string }) =>
    request("/api/finance", { method: "POST", body: JSON.stringify(data) }),

  getInstructions: () => request<{ instructions: string; constitution: string }>("/api/instructions"),
  setInstructions: (content: string) =>
    request("/api/instructions", { method: "PUT", body: JSON.stringify({ content }) }),
};

export type Space = {
  id: number;
  name: string;
  description?: string;
  asset_count?: number;
  alias_count?: number;
  created_at?: string;
  updated_at?: string;
};

export type Alias = { id: number; space_id: number; alias: string };
export type Asset = {
  id: number;
  space_id: number;
  kind: string;
  title?: string;
  url?: string;
  mime?: string;
  status: string;
  text_chars?: number;
  chunk_count?: number;
  error?: string;
  extracted_text?: string;
  created_at?: string;
};

export type SpaceDetail = { space: Space; assets: Asset[]; aliases: Alias[] };

export type Contact = { id: number; name: string; company?: string; email?: string; status?: string; [k: string]: any };
export type Company = { id: number; name: string; website?: string; industry?: string; [k: string]: any };
export type Task = { id: number; title: string; description?: string; status?: string; priority?: number; [k: string]: any };
export type Goal = { id: number; title: string; detail?: string; status?: string; priority?: number; [k: string]: any };
export type Reminder = { id: number; text: string; due_at: string; status?: string; repeat?: string; [k: string]: any };
export type Lesson = { id: number; lesson: string; situation?: string; tags?: string; [k: string]: any };
export type Skill = { id: number; name: string; when_to_use?: string; steps?: string; [k: string]: any };
export type Approval = { id: number; summary?: string; tool_name?: string; status?: string; [k: string]: any };

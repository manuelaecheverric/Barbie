import { supabase } from "./supabase";

const API_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

function readDetail(data, fallback) {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((d) => d.msg).join(". ");
  return fallback;
}

/** fetch con el token de Supabase. Toda la API está protegida. */
async function request(path, { method = "GET", json, form } = {}) {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  if (!token) throw new ApiError("Tu sesión terminó. Inicia sesión de nuevo.", 401);

  const headers = { Authorization: `Bearer ${token}` };
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form) {
    body = form;
  }

  let res;
  try {
    res = await fetch(`${API_URL}${path}`, { method, headers, body });
  } catch {
    throw new ApiError("No hay conexión con el servidor. Revisa tu internet o que el backend esté encendido.");
  }

  if (res.status === 204) return null;
  const payload = await res.json().catch(() => null);

  if (res.status === 401) {
    await supabase.auth.signOut();
    throw new ApiError(readDetail(payload, "Tu sesión terminó. Inicia sesión de nuevo."), 401);
  }
  if (!res.ok) {
    throw new ApiError(readDetail(payload, `Error del servidor (${res.status}).`), res.status);
  }
  return payload;
}

export const api = {
  me: () => request("/api/me"),
  ask: (question, conversationId) =>
    request("/api/chat", { method: "POST", json: { question, conversation_id: conversationId || null } }),
  conversations: () => request("/api/conversations"),
  messages: (id) => request(`/api/conversations/${id}/messages`),
  deleteConversation: (id) => request(`/api/conversations/${id}`, { method: "DELETE" }),
  documents: () => request("/api/documents"),
  uploadDocument: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/api/documents", { method: "POST", form });
  },
  deleteDocument: (id) => request(`/api/documents/${id}`, { method: "DELETE" }),
};

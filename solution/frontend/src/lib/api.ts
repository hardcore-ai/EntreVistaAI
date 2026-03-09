import axios from "axios";
import Cookies from "js-cookie";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = Cookies.get("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      Cookies.remove("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

// ─── Auth ─────────────────────────────────────────────────────────────────────
export async function login(email: string, password: string) {
  const params = new URLSearchParams({ username: email, password });
  const { data } = await api.post("/auth/token", params, {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  Cookies.set("token", data.access_token, { expires: 1 });
  return data;
}

export async function getMe() {
  const { data } = await api.get("/auth/me");
  return data;
}

// ─── Campaigns ────────────────────────────────────────────────────────────────
export async function getCampaigns() {
  const { data } = await api.get("/api/v1/campaigns");
  return data;
}

export async function getCampaign(id: string) {
  const { data } = await api.get(`/api/v1/campaigns/${id}`);
  return data;
}

export async function createCampaign(payload: any) {
  const { data } = await api.post("/api/v1/campaigns", payload);
  return data;
}

export async function updateCampaign(id: string, payload: any) {
  const { data } = await api.patch(`/api/v1/campaigns/${id}`, payload);
  return data;
}

// ─── Candidates ───────────────────────────────────────────────────────────────
export async function getCandidates(params?: { campaign_id?: string; status?: string }) {
  const { data } = await api.get("/api/v1/candidates", { params });
  return data;
}

// ─── Evaluations ──────────────────────────────────────────────────────────────
export async function getEvaluations(params?: { status?: string; campaign_id?: string }) {
  const { data } = await api.get("/api/v1/evaluations", { params });
  return data;
}

export async function getEvaluation(id: string) {
  const { data } = await api.get(`/api/v1/evaluations/${id}`);
  return data;
}

export async function submitDecision(id: string, decision: "approved" | "rejected", notes?: string) {
  const { data } = await api.post(`/api/v1/evaluations/${id}/decide`, { decision, notes });
  return data;
}

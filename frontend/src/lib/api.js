import axios from "axios";

export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const client = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  timeout: 20000,
});

// Request interceptor: attach Bearer token automatically
client.interceptors.request.use((config) => {
  const token = localStorage.getItem("safenet_access_token");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: silent refresh-and-retry on 401
let isRefreshing = false;
let pendingQueue = [];

function flushQueue(error, token) {
  pendingQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(token);
  });
  pendingQueue = [];
}

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config;
    const isAuthEndpoint =
      originalRequest?.url?.includes("/auth/login") || originalRequest?.url?.includes("/auth/register");

    if (error.response?.status !== 401 || originalRequest?._retry || isAuthEndpoint) {
      const detail =
        error?.response?.data?.detail || error?.response?.data?.error || error?.message || "Request failed";
      return Promise.reject(new Error(typeof detail === "string" ? detail : JSON.stringify(detail)));
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        pendingQueue.push({ resolve, reject });
      }).then((token) => {
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers.Authorization = `Bearer ${token}`;
        return client(originalRequest);
      });
    }

    originalRequest._retry = true;
    isRefreshing = true;

    try {
      const refreshToken = localStorage.getItem("safenet_refresh_token");
      if (!refreshToken) throw error;

      const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken,
      });

      localStorage.setItem("safenet_access_token", data.access_token);
      if (data.refresh_token) {
        localStorage.setItem("safenet_refresh_token", data.refresh_token);
      }

      flushQueue(null, data.access_token);
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
      return client(originalRequest);
    } catch (refreshError) {
      flushQueue(refreshError, null);
      localStorage.removeItem("safenet_access_token");
      localStorage.removeItem("safenet_refresh_token");
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

const qs = (params = {}) => {
  const clean = Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== "");
  return new URLSearchParams(clean).toString();
};

// ── Scam Detection — /calls ──────────────────────────────────────
export const Scam = {
  analyze: (payload) => client.post("/calls/analyze", payload).then((r) => r.data),
  reports: (params) => client.get(`/calls/reports?${qs(params)}`).then((r) => r.data),
  report: (id) => client.get(`/calls/reports/${id}`).then((r) => r.data),
  updateStatus: (id, new_status, officer_notes) =>
    client
      .patch(`/calls/reports/${id}/status?${qs({ new_status, officer_notes })}`)
      .then((r) => r.data),
  stats: (days_back = 30) => client.get(`/calls/stats?${qs({ days_back })}`).then((r) => r.data),
};

// ── Counterfeit Detection — /currency ────────────────────────────
export const Currency = {
  verify: (formData) =>
    client
      .post("/currency/verify", formData, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data),
  reports: (params) => client.get(`/currency/reports?${qs(params)}`).then((r) => r.data),
  report: (id) => client.get(`/currency/reports/${id}`).then((r) => r.data),
  stats: (days_back = 30) => client.get(`/currency/stats?${qs({ days_back })}`).then((r) => r.data),
};

// ── Fraud Graph Intelligence — /fraud ────────────────────────────
export const Fraud = {
  queryGraph: (payload) => client.post("/fraud/graph/query", payload).then((r) => r.data),
  register: (params) => client.post(`/fraud/register?${qs(params)}`).then((r) => r.data),
  link: (params) => client.post(`/fraud/link?${qs(params)}`).then((r) => r.data),
  cases: (params) => client.get(`/fraud/cases?${qs(params)}`).then((r) => r.data),
  createCase: (params) => client.post(`/fraud/cases?${qs(params)}`).then((r) => r.data),
  case: (id) => client.get(`/fraud/cases/${id}`).then((r) => r.data),
};

// ── Geospatial Intelligence — /heatmap ───────────────────────────
export const Geo = {
  crimes: (params) => client.get(`/heatmap/crimes?${qs(params)}`).then((r) => r.data),
  patrolPriorities: (params) =>
    client.get(`/heatmap/patrol-priorities?${qs(params)}`).then((r) => r.data),
  stateSummary: (days_back = 30) =>
    client.get(`/heatmap/state-summary?${qs({ days_back })}`).then((r) => r.data),
  cityHotspots: (params) => client.get(`/heatmap/city-hotspots?${qs(params)}`).then((r) => r.data),
};

// ── Citizen Shield — /citizen ─────────────────────────────────────
export const Citizen = {
  assess: (payload) => client.post("/citizen/assess", payload).then((r) => r.data),
  scamTypes: () => client.get("/citizen/scam-types").then((r) => r.data),
  helplines: () => client.get("/citizen/helplines").then((r) => r.data),
};

// ── Evidence Packages — /reports ─────────────────────────────────
export const Evidence = {
  generate: (payload) => client.post("/reports/generate", payload).then((r) => r.data),
  downloadUrl: (packageId) => `${BASE_URL}/api/v1/reports/download/${packageId}`,
  auditTrail: (params) => client.get(`/reports/audit-trail?${qs(params)}`).then((r) => r.data),
};

// ── Analytics & Dashboard — /analytics ───────────────────────────
export const Analytics = {
  dashboard: (days_back = 30) =>
    client.get(`/analytics/dashboard?${qs({ days_back })}`).then((r) => r.data),
  trends: (params) => client.get(`/analytics/trends?${qs(params)}`).then((r) => r.data),
  modelPerformance: (days_back = 7) =>
    client.get(`/analytics/model-performance?${qs({ days_back })}`).then((r) => r.data),
};

export const health = () => axios.get(`${BASE_URL}/health`).then((r) => r.data);

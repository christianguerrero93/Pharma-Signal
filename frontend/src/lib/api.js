import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

export const setAuthToken = (token) => {
  api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
};

export const clearAuthToken = () => {
  delete api.defaults.headers.common["Authorization"];
};

// Pre-attach token from localStorage at module load so requests right after
// page reload don't fire without it (AuthProvider then re-validates).
const t = typeof window !== "undefined" && window.localStorage?.getItem("ps_token");
if (t) setAuthToken(t);

export const fmtMoney = (n) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(n || 0);

export const fmtNum = (n, d = 0) =>
  new Intl.NumberFormat("en-US", { maximumFractionDigits: d }).format(n || 0);

export const fmtPct = (n, d = 1) =>
  `${(n ?? 0).toFixed(d)}%`;

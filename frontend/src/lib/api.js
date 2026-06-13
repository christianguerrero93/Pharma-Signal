import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const api = axios.create({
  baseURL: API,
  headers: { "Content-Type": "application/json" },
});

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

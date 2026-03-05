import axios from "axios";

const AUTH_TOKEN_KEY = "auth_token";
type AuthErrorHandlers = {
  onUnauthorized?: () => void;
  onForbidden?: () => void;
};

type ApiErrorObjectDetail = {
  message?: unknown;
  explanation?: unknown;
  suggestions?: unknown;
  context?: unknown;
};

type ValidationErrorItem = {
  loc?: unknown;
  msg?: unknown;
};

type FormatApiErrorOptions = {
  fallbackMessage: string;
  detailMap?: Record<string, string>;
  statusMap?: Record<number, string>;
};

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || "http://127.0.0.1:8000";

const API = axios.create({
  baseURL: API_BASE_URL,
});
let authErrorHandlers: AuthErrorHandlers = {};

export function setAuthToken(token: string | null) {
  if (token) {
    localStorage.setItem(AUTH_TOKEN_KEY, token);
    API.defaults.headers.common.Authorization = `Bearer ${token}`;
    return;
  }
  localStorage.removeItem(AUTH_TOKEN_KEY);
  delete API.defaults.headers.common.Authorization;
}

export function loadStoredAuthToken() {
  return localStorage.getItem(AUTH_TOKEN_KEY);
}

export function setAuthErrorHandlers(handlers: AuthErrorHandlers) {
  authErrorHandlers = handlers;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return !!value && typeof value === "object" && !Array.isArray(value);
}

function formatValidationErrors(detail: unknown) {
  if (!Array.isArray(detail)) return null;
  const parts = detail
    .map(item => {
      const entry = item as ValidationErrorItem;
      const msg = typeof entry.msg === "string" ? entry.msg : "";
      if (!msg) return "";
      const location = Array.isArray(entry.loc)
        ? entry.loc.filter(part => typeof part === "string" || typeof part === "number").join(".")
        : "";
      return location ? `${location}: ${msg}` : msg;
    })
    .filter(Boolean);
  return parts.length > 0 ? parts.join(" ") : null;
}

function formatObjectDetail(detail: unknown) {
  if (!isRecord(detail)) return null;
  const payload = detail as ApiErrorObjectDetail;
  const parts: string[] = [];

  if (typeof payload.message === "string") {
    parts.push(payload.message);
  }
  if (typeof payload.explanation === "string") {
    parts.push(payload.explanation);
  }

  if (isRecord(payload.context)) {
    const dayLabel = typeof payload.context.day_label === "string" ? payload.context.day_label : undefined;
    const hourLabel = typeof payload.context.hour_label === "string" ? payload.context.hour_label : undefined;
    if (dayLabel && hourLabel) {
      parts.push(`First uncovered time: ${dayLabel} at ${hourLabel}.`);
    }

    if (
      typeof payload.context.assigned_staff === "number"
      && typeof payload.context.required_staff === "number"
    ) {
      parts.push(`Assigned staff: ${payload.context.assigned_staff}, required: ${payload.context.required_staff}.`);
    }

    if (typeof payload.context.required_managers_per_hour === "number") {
      parts.push(`Required managers per hour: ${payload.context.required_managers_per_hour}.`);
    }

    if (
      typeof payload.context.user_id === "number"
      && typeof payload.context.assigned_shifts === "number"
      && typeof payload.context.required_shifts === "number"
    ) {
      parts.push(`User ${payload.context.user_id} shifts: ${payload.context.assigned_shifts}/${payload.context.required_shifts}.`);
    }
  }

  if (Array.isArray(payload.suggestions)) {
    const suggestions = payload.suggestions.filter(item => typeof item === "string") as string[];
    if (suggestions.length > 0) {
      parts.push(`Try: ${suggestions.slice(0, 2).join(" ")}`);
    }
  }

  return parts.length > 0 ? parts.join(" ") : null;
}

export function formatApiError(error: unknown, options: FormatApiErrorOptions) {
  const detail = (error as any)?.response?.data?.detail;
  const status = (error as any)?.response?.status as number | undefined;

  if (typeof detail === "string") {
    return options.detailMap?.[detail] ?? detail;
  }

  const structuredMessage = formatObjectDetail(detail);
  if (structuredMessage) {
    return structuredMessage;
  }

  const validationMessage = formatValidationErrors(detail);
  if (validationMessage) {
    return validationMessage;
  }

  if (typeof status === "number" && options.statusMap?.[status]) {
    return options.statusMap[status];
  }

  if ((error as any)?.request && !(error as any)?.response) {
    const apiBase = API.defaults.baseURL || API_BASE_URL;
    const pageProtocol = typeof window !== "undefined" ? window.location.protocol : "";
    if (pageProtocol === "https:" && /^http:\/\//i.test(apiBase)) {
      return "Could not reach the server. Your app is on HTTPS but API_BASE_URL is HTTP, which browsers block. Use an HTTPS backend URL.";
    }
    return `Could not reach the server at ${apiBase}. Check backend uptime, CORS_ALLOW_ORIGINS, and REACT_APP_API_BASE_URL.`;
  }

  return options.fallbackMessage;
}

API.interceptors.response.use(
  response => response,
  error => {
    const status = error?.response?.status;
    if (status === 401) {
      authErrorHandlers.onUnauthorized?.();
    } else if (status === 403) {
      authErrorHandlers.onForbidden?.();
    }
    return Promise.reject(error);
  }
);

export default API;

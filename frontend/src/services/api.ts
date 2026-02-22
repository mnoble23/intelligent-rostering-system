import axios from "axios";

const AUTH_TOKEN_KEY = "auth_token";
type AuthErrorHandlers = {
  onUnauthorized?: () => void;
  onForbidden?: () => void;
};

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
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

const initialToken = loadStoredAuthToken();
if (initialToken) {
  API.defaults.headers.common.Authorization = `Bearer ${initialToken}`;
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

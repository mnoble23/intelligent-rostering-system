import axios from "axios";

const AUTH_TOKEN_KEY = "auth_token";

const API = axios.create({
  baseURL: "http://127.0.0.1:8000",
});

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

const initialToken = loadStoredAuthToken();
if (initialToken) {
  API.defaults.headers.common.Authorization = `Bearer ${initialToken}`;
}

export default API;

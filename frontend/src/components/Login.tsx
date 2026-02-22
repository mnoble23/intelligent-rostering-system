import { useState } from "react";
import API, { setAuthToken } from "../services/api";
import "./Login.css";

interface AuthUser {
  id: number;
  name: string;
  role: "manager" | "staff";
  is_active: boolean;
}

interface LoginProps {
  onLoginSuccess: (user: AuthUser) => void;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setStatus("");

    if (!name.trim() || !password) {
      setStatus("Enter your name and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await API.post<LoginResponse>("/auth/login", {
        name: name.trim(),
        password,
      });
      setAuthToken(response.data.access_token);
      onLoginSuccess(response.data.user);
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-page__card" onSubmit={handleSubmit}>
        <h1>Roster OS</h1>
        <p>Sign in to continue.</p>

        <label>
          Name
          <input
            type="text"
            value={name}
            onChange={event => setName(event.target.value)}
            disabled={isSubmitting}
            autoComplete="username"
          />
        </label>

        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={event => setPassword(event.target.value)}
            disabled={isSubmitting}
            autoComplete="current-password"
          />
        </label>

        {status && <p className="login-page__status">{status}</p>}

        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? "Signing in..." : "Sign In"}
        </button>
      </form>
    </main>
  );
}

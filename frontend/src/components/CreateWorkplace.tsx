import { useState } from "react";
import API, { formatApiError, setAuthToken } from "../services/api";
import "./Login.css";

interface AuthUser {
  id: number;
  name: string;
  role: "manager" | "staff";
  is_active: boolean;
}

interface CreateWorkplaceProps {
  onCreateSuccess: (user: AuthUser) => void;
  onBack: () => void;
}

interface CreateWorkplaceResponse {
  access_token: string;
  token_type: string;
  user: AuthUser;
}

export default function CreateWorkplace({ onCreateSuccess, onBack }: CreateWorkplaceProps) {
  const [workplaceName, setWorkplaceName] = useState("");
  const [managerName, setManagerName] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setStatus("");

    if (!workplaceName.trim() || !managerName.trim() || !password) {
      setStatus("Enter workplace name, manager name, and password.");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await API.post<CreateWorkplaceResponse>("/onboarding/create-workplace", {
        workplace_name: workplaceName.trim(),
        manager_name: managerName.trim(),
        password,
      });
      setAuthToken(response.data.access_token);
      onCreateSuccess(response.data.user);
    } catch (err: unknown) {
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to create workplace.",
        detailMap: {
          "Workplace has already been created": "A workplace is already set up. Sign in with the existing manager account.",
          "Workplace name is required": "Enter a workplace name.",
          "Manager name is required": "Enter a manager name.",
          "password must be at least 8 characters": "Password must be at least 8 characters.",
        },
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <form className="login-page__card" onSubmit={handleSubmit}>
        <h1>Create Workplace</h1>
        <p>Set up your first manager account.</p>

        <label>
          Workplace name
          <input
            type="text"
            value={workplaceName}
            onChange={event => setWorkplaceName(event.target.value)}
            disabled={isSubmitting}
            autoComplete="organization"
          />
        </label>

        <label>
          Manager name
          <input
            type="text"
            value={managerName}
            onChange={event => setManagerName(event.target.value)}
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
            autoComplete="new-password"
          />
        </label>

        {status && <p className="login-page__status">{status}</p>}

        <div className="login-page__actions">
          <button type="submit" disabled={isSubmitting}>
            {isSubmitting ? "Creating..." : "Create Workplace"}
          </button>
          <button type="button" className="login-page__button--secondary" onClick={onBack} disabled={isSubmitting}>
            Back to Selection
          </button>
        </div>
      </form>
    </main>
  );
}

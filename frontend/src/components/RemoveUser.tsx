import { useEffect, useMemo, useState } from "react";
import API from "../services/api";
import "./RemoveUser.css";

interface User {
  id: number;
  name: string;
  role: "manager" | "staff";
  min_hours: number;
  max_hours: number;
}

interface RemoveUserProps {
  refreshRoster?: () => void;
}

export default function RemoveUser({ refreshRoster }: RemoveUserProps) {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "loading" | "success" | "error">("idle");

  const loadUsers = async () => {
    try {
      const response = await API.get<User[]>("/users");
      setUsers(response.data);
      setSelectedUserId(current => {
        if (!response.data.length) return "";
        if (current && response.data.some(user => String(user.id) === current)) return current;
        return String(response.data[0].id);
      });
    } catch (err) {
      console.error(err);
      setStatus("Failed to load users.");
      setStatusType("error");
    }
  };

  useEffect(() => {
    loadUsers();
  }, []);

  const selectedUser = useMemo(
    () => users.find(user => String(user.id) === selectedUserId) ?? null,
    [users, selectedUserId]
  );

  const handleRemove = async () => {
    if (!selectedUser) {
      setStatus("Pick a user first.");
      setStatusType("error");
      return;
    }

    const confirmed = window.confirm(
      `Remove user ${selectedUser.name}? This will delete their availability and shift assignments.`
    );
    if (!confirmed) return;

    setStatus("Removing user...");
    setStatusType("loading");

    try {
      await API.delete(`/users/${selectedUser.id}`);
      setStatus(`User ${selectedUser.name} was removed.`);
      setStatusType("success");
      await loadUsers();
      if (refreshRoster) refreshRoster();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : "Failed to remove user.");
      setStatusType("error");
    }
  };

  return (
    <section className="remove-user">
      <div className="remove-user__shell">
        <header className="remove-user__hero">
          <h2>Remove User</h2>
          <p className="remove-user__lead">
            Select a user and permanently remove them from the system.
          </p>
        </header>

        <div className="remove-user__panel">
          <div className="remove-user__status-row">
            <span className="remove-user__label">System Status</span>
            <span className={`remove-user__badge remove-user__badge--${statusType}`}>
              {statusType === "loading" ? "Removing" : statusType === "success" ? "Done" : statusType === "error" ? "Attention" : "Standby"}
            </span>
          </div>

          {statusType === "loading" && (
            <div className="remove-user__loader" aria-hidden="true">
              <span />
            </div>
          )}

          <p className={`remove-user__message remove-user__message--${statusType}`}>
            {status || "Select a user to remove."}
          </p>

          <div className="remove-user__actions">
            <label className="remove-user__control">
              User
              <select
                className="remove-user__select"
                value={selectedUserId}
                onChange={event => setSelectedUserId(event.target.value)}
                disabled={statusType === "loading" || users.length === 0}
              >
                {users.length === 0 ? (
                  <option value="">No users</option>
                ) : (
                  users.map(user => (
                    <option key={user.id} value={String(user.id)}>
                      {user.name} ({user.role})
                    </option>
                  ))
                )}
              </select>
            </label>
          </div>

          {selectedUser && (
            <p className="remove-user__summary">
              Selected: <strong>{selectedUser.name}</strong> ({selectedUser.role}) | Hours:{" "}
              {selectedUser.min_hours} - {selectedUser.max_hours}
            </p>
          )}

          <div className="remove-user__actions">
            <button
              type="button"
              className="remove-user__button"
              onClick={handleRemove}
              disabled={!selectedUser || statusType === "loading"}
            >
              {statusType === "loading" ? "Removing..." : "Remove User"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

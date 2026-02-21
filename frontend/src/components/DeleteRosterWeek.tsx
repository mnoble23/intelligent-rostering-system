import { useEffect, useState } from "react";
import API from "../services/api";
import "./DeleteRosterWeek.css";

interface DeleteRosterWeekProps {
  selectedWeek?: string;
  availableWeeks?: string[];
  refreshRoster?: () => void;
  refreshWeeks?: () => void;
}

function formatWeekOption(weekStartDate: string) {
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const dayOfWeek = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayOfWeek);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNumber = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  const dd = String(day).padStart(2, "0");
  const mm = String(month).padStart(2, "0");
  const yyyy = String(year);
  return `Week ${weekNumber} - ${dd}/${mm}/${yyyy}`;
}

export default function DeleteRosterWeek({
  selectedWeek,
  availableWeeks = [],
  refreshRoster,
  refreshWeeks,
}: DeleteRosterWeekProps) {
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [targetWeek, setTargetWeek] = useState(selectedWeek ?? "");

  useEffect(() => {
    if (selectedWeek) {
      setTargetWeek(current => current || selectedWeek);
      return;
    }
    if (!selectedWeek && availableWeeks.length === 0) {
      setTargetWeek("");
    }
  }, [selectedWeek, availableWeeks.length]);

  useEffect(() => {
    if (targetWeek && availableWeeks.includes(targetWeek)) return;
    if (availableWeeks.length > 0) {
      setTargetWeek(availableWeeks[0]);
      return;
    }
    setTargetWeek("");
  }, [availableWeeks, targetWeek]);

  const handleDelete = async () => {
    if (!targetWeek) {
      setStatus("Pick a roster week first.");
      setStatusType("error");
      return;
    }

    const confirmed = window.confirm(
      `Delete roster week ${targetWeek}? This permanently removes all shifts and assignments for that week.`
    );
    if (!confirmed) return;

    setStatus("Deleting roster week...");
    setStatusType("loading");

    try {
      await API.delete(`/roster/week/${targetWeek}`);
      setStatus(`Roster week ${targetWeek} deleted.`);
      setStatusType("success");
      if (refreshWeeks) refreshWeeks();
      if (refreshRoster) refreshRoster();
    } catch (err: any) {
      const detail = err?.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : "Failed to delete roster week.");
      setStatusType("error");
    }
  };

  return (
    <section className="delete-week">
      <div className="delete-week__shell">
        <header className="delete-week__hero">
          <h2>Delete Weekly Roster</h2>
          <p className="delete-week__lead">
            Remove all shifts and assignments for a selected week. This cannot be undone.
          </p>
        </header>

        <div className="delete-week__panel">
          <div className="delete-week__status-row">
            <span className="delete-week__label">System Status</span>
            <span className={`delete-week__badge delete-week__badge--${statusType}`}>
              {statusType === "loading" ? "Deleting" : statusType === "success" ? "Done" : statusType === "error" ? "Attention" : "Standby"}
            </span>
          </div>

          {statusType === "loading" && (
            <div className="delete-week__loader" aria-hidden="true">
              <span />
            </div>
          )}

          <p className={`delete-week__message delete-week__message--${statusType}`}>
            {status || "Select a week and confirm deletion."}
          </p>

          <div className="delete-week__actions">
            <label className="delete-week__weeks-control">
              Week
              <select
                className="delete-week__weeks-input"
                value={targetWeek}
                onChange={event => setTargetWeek(event.target.value)}
                disabled={statusType === "loading" || availableWeeks.length === 0}
              >
                {availableWeeks.length === 0 ? (
                  <option value="">No roster weeks</option>
                ) : (
                  availableWeeks.map(week => (
                    <option key={week} value={week}>
                      {formatWeekOption(week)}
                    </option>
                  ))
                )}
              </select>
            </label>
          </div>

          <div className="delete-week__actions">
            <button
              type="button"
              className="delete-week__button"
              onClick={handleDelete}
              disabled={!targetWeek || statusType === "loading"}
            >
              {statusType === "loading" ? "Deleting..." : "Delete Selected Week"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

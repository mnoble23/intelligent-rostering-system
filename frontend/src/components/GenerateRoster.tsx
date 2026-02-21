import API from "../services/api";
import { useState } from "react";
import "./GenerateRoster.css";

interface GenerateRosterProps {
  refreshRoster?: () => void;
  refreshWeeks?: () => void;
  startDate?: string;
}

export default function GenerateRoster({ refreshRoster, refreshWeeks, startDate }: GenerateRosterProps) {
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [weeks, setWeeks] = useState(1);

  const handleGenerate = async () => {
    setStatus(`Generating roster for ${weeks} week${weeks === 1 ? "" : "s"}...`);
    setStatusType("loading");
    try {
      await API.post("/roster/generate", startDate ? { weeks, start_date: startDate } : { weeks });
      setStatus(`Roster generated successfully for ${weeks} week${weeks === 1 ? "" : "s"}. Dashboard data is now up to date.`);
      setStatusType("success");
      if (refreshRoster) {
        refreshRoster();
      }
      if (refreshWeeks) {
        refreshWeeks();
      }
    } catch (err) {
      console.error(err);
      setStatus("Generation failed. Please check availability and staffing limits, then try again.");
      setStatusType("error");
    }
  };

  return (
    <section className="generate-roster">
      <div className="generate-roster__shell">
        <header className="generate-roster__hero">
          <p className="generate-roster__eyebrow">Automation Control</p>
          <h2>Generate Weekly Roster</h2>
          <p className="generate-roster__lead">
            Build a fresh roster from submitted availability and staffing constraints in one step.
          </p>
        </header>

        <div className="generate-roster__panel">
          <div className="generate-roster__status-row">
            <span className="generate-roster__label">System Status</span>
            <span className={`generate-roster__badge generate-roster__badge--${statusType}`}>
              {statusType === "loading" ? "Generating" : statusType === "success" ? "Ready" : statusType === "error" ? "Attention" : "Standby"}
            </span>
          </div>

          {statusType === "loading" && (
            <div className="generate-roster__loader" aria-hidden="true">
              <span />
            </div>
          )}

          <p className={`generate-roster__message generate-roster__message--${statusType}`}>
            {status || "Click generate to build this week's roster."}
          </p>

          <div className="generate-roster__actions">
            <label className="generate-roster__weeks-control">
              Number of weeks
              <input
                className="generate-roster__weeks-input"
                type="number"
                min={1}
                max={52}
                value={weeks}
                onChange={event => setWeeks(Math.min(52, Math.max(1, Number(event.target.value) || 1)))}
                disabled={statusType === "loading"}
              />
            </label>
          </div>

          <div className="generate-roster__actions">
            <button type="button" onClick={handleGenerate} disabled={statusType === "loading"} className="generate-roster__button">
              {statusType === "loading" ? "Generating..." : "Generate Roster"}
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}

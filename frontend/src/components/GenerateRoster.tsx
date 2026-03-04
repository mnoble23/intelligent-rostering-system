import API from "../services/api";
import { useEffect, useState } from "react";
import "./GenerateRoster.css";

interface GenerateRosterProps {
  refreshRoster?: () => void;
  refreshWeeks?: () => void;
  startDate?: string;
}

type RosterErrorDetail = {
  message?: string;
  explanation?: string;
  suggestions?: string[];
  context?: {
    day_label?: string;
    hour_label?: string;
    assigned_staff?: number;
    required_staff?: number;
    required_managers_per_hour?: number;
    user_id?: number;
    assigned_shifts?: number;
    required_shifts?: number;
  };
};

function buildRosterErrorMessage(err: unknown) {
  const detail = (err as any)?.response?.data?.detail;
  if (typeof detail === "string") {
    return detail;
  }

  if (detail && typeof detail === "object") {
    const parsed = detail as RosterErrorDetail;
    const parts: string[] = [];
    if (parsed.message) {
      parts.push(parsed.message);
    }
    if (parsed.explanation) {
      parts.push(parsed.explanation);
    }

    const contextParts: string[] = [];
    if (parsed.context?.day_label && parsed.context?.hour_label) {
      contextParts.push(`First uncovered time: ${parsed.context.day_label} at ${parsed.context.hour_label}.`);
    }
    if (
      typeof parsed.context?.assigned_staff === "number"
      && typeof parsed.context?.required_staff === "number"
    ) {
      contextParts.push(
        `Assigned staff: ${parsed.context.assigned_staff}, required: ${parsed.context.required_staff}.`
      );
    }
    if (typeof parsed.context?.required_managers_per_hour === "number") {
      contextParts.push(`Required managers per hour: ${parsed.context.required_managers_per_hour}.`);
    }
    if (
      typeof parsed.context?.user_id === "number"
      && typeof parsed.context?.assigned_shifts === "number"
      && typeof parsed.context?.required_shifts === "number"
    ) {
      contextParts.push(
        `User ${parsed.context.user_id} shifts: ${parsed.context.assigned_shifts}/${parsed.context.required_shifts}.`
      );
    }
    if (contextParts.length > 0) {
      parts.push(contextParts.join(" "));
    }

    if (Array.isArray(parsed.suggestions) && parsed.suggestions.length > 0) {
      parts.push(`Try: ${parsed.suggestions.slice(0, 2).join(" ")}`);
    }

    if (parts.length > 0) {
      return parts.join(" ");
    }
  }

  return "Generation failed. Please check availability and staffing limits, then try again.";
}

function toIsoWeek(value?: string) {
  if (!value) return "";
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  const dayOfWeek = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - dayOfWeek);
  const yearStart = new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
  const weekNo = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
  return `${date.getUTCFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

function isoWeekToMonday(value: string) {
  const [yearPart, weekPart] = value.split("-W");
  const year = Number(yearPart);
  const week = Number(weekPart);
  const jan4 = new Date(Date.UTC(year, 0, 4));
  const jan4Day = jan4.getUTCDay() || 7;
  const monday = new Date(jan4);
  monday.setUTCDate(jan4.getUTCDate() - jan4Day + 1 + (week - 1) * 7);
  const mm = String(monday.getUTCMonth() + 1).padStart(2, "0");
  const dd = String(monday.getUTCDate()).padStart(2, "0");
  return `${monday.getUTCFullYear()}-${mm}-${dd}`;
}

export default function GenerateRoster({ refreshRoster, refreshWeeks, startDate }: GenerateRosterProps) {
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "loading" | "success" | "error">("idle");
  const [targetWeek, setTargetWeek] = useState(toIsoWeek(startDate));

  useEffect(() => {
    setTargetWeek(toIsoWeek(startDate));
  }, [startDate]);

  const handleGenerate = async () => {
    if (!targetWeek) {
      setStatus("Pick a week first.");
      setStatusType("error");
      return;
    }
    setStatus("Generating roster...");
    setStatusType("loading");
    try {
      const mondayDate = isoWeekToMonday(targetWeek);
      await API.post("/roster/generate", { weeks: 1, start_date: mondayDate });
      setStatus("Roster generated successfully for selected week. Dashboard data is now up to date.");
      setStatusType("success");
      if (refreshRoster) {
        refreshRoster();
      }
      if (refreshWeeks) {
        refreshWeeks();
      }
    } catch (err) {
      console.error(err);
      setStatus(buildRosterErrorMessage(err));
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
              Week
              <input
                className="generate-roster__weeks-input"
                type="week"
                value={targetWeek}
                onChange={event => setTargetWeek(event.target.value)}
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

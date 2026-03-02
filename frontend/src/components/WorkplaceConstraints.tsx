import { useEffect, useState } from "react";
import API from "../services/api";
import "./WorkplaceConstraints.css";

interface WorkplaceConstraintsResponse {
  workplace_id: number;
  min_staff_per_shift: number;
  min_managers_per_hour: number;
}

export default function WorkplaceConstraints() {
  const [constraints, setConstraints] = useState<WorkplaceConstraintsResponse | null>(null);
  const [status, setStatus] = useState("");
  const [statusType, setStatusType] = useState<"idle" | "loading" | "success" | "error">("idle");

  useEffect(() => {
    let cancelled = false;

    async function loadConstraints() {
      setStatus("Loading workplace constraints...");
      setStatusType("loading");
      try {
        const response = await API.get<WorkplaceConstraintsResponse>("/workplace/constraints");
        if (!cancelled) {
          setConstraints(response.data);
          setStatus("Constraints loaded.");
          setStatusType("success");
        }
      } catch (err) {
        console.error(err);
        if (!cancelled) {
          setStatus("Failed to load workplace constraints.");
          setStatusType("error");
        }
      }
    }

    loadConstraints();

    return () => {
      cancelled = true;
    };
  }, []);

  const updateConstraint = (field: "min_staff_per_shift" | "min_managers_per_hour", value: number) => {
    setConstraints(current => {
      if (!current) return current;
      return { ...current, [field]: value };
    });
  };

  const handleSave = async () => {
    if (!constraints) return;

    setStatus("Saving workplace constraints...");
    setStatusType("loading");
    try {
      const response = await API.put<WorkplaceConstraintsResponse>("/workplace/constraints", {
        min_staff_per_shift: constraints.min_staff_per_shift,
        min_managers_per_hour: constraints.min_managers_per_hour,
      });
      setConstraints(response.data);
      setStatus("Constraints saved.");
      setStatusType("success");
    } catch (err: any) {
      console.error(err);
      const detail = err?.response?.data?.detail;
      setStatus(typeof detail === "string" ? detail : "Failed to save workplace constraints.");
      setStatusType("error");
    }
  };

  return (
    <section className="workplace-constraints">
      <div className="workplace-constraints__shell">
        <header className="workplace-constraints__hero">
          <p className="workplace-constraints__eyebrow">Workplace Settings</p>
          <h2>Roster Constraints</h2>
          <p>Configure staffing targets used during roster generation and coverage reporting.</p>
        </header>

        <div className="workplace-constraints__panel">
          <label className="workplace-constraints__field">
            <span>Min staff per shift</span>
            <input
              type="number"
              min={1}
              max={20}
              value={constraints?.min_staff_per_shift ?? 2}
              onChange={event => updateConstraint("min_staff_per_shift", Number(event.target.value))}
              disabled={!constraints || statusType === "loading"}
            />
          </label>

          <label className="workplace-constraints__field">
            <span>Min managers per hour</span>
            <input
              type="number"
              min={0}
              max={10}
              value={constraints?.min_managers_per_hour ?? 1}
              onChange={event => updateConstraint("min_managers_per_hour", Number(event.target.value))}
              disabled={!constraints || statusType === "loading"}
            />
          </label>

          <button type="button" className="workplace-constraints__save" onClick={handleSave} disabled={!constraints || statusType === "loading"}>
            {statusType === "loading" ? "Saving..." : "Save Constraints"}
          </button>

          <p className={`workplace-constraints__status workplace-constraints__status--${statusType}`}>
            {status || "Adjust values and save to update workplace-level constraints."}
          </p>
        </div>
      </div>
    </section>
  );
}

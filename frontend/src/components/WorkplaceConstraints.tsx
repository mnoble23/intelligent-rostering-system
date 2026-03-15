import { useEffect, useState } from "react";
import API, { formatApiError } from "../services/api";
import "./WorkplaceConstraints.css";

interface WorkplaceConstraintsResponse {
  workplace_id: number;
  min_staff_per_shift: number;
  min_managers_per_hour: number;
  max_consecutive_shifts: number;
  min_hours_between_shifts: number;
  business_start_hour: number;
  business_end_hour: number;
}

function validateConstraints(values: WorkplaceConstraintsResponse) {
  const fields = [
    values.min_staff_per_shift,
    values.min_managers_per_hour,
    values.max_consecutive_shifts,
    values.min_hours_between_shifts,
    values.business_start_hour,
    values.business_end_hour,
  ];

  if (fields.some(value => !Number.isFinite(value))) {
    return "All constraint values must be valid numbers.";
  }
  if (fields.some(value => !Number.isInteger(value))) {
    return "All constraints must be whole numbers.";
  }
  if (values.min_staff_per_shift < 1 || values.min_staff_per_shift > 20) {
    return "Min staff per shift must be between 1 and 20.";
  }
  if (values.min_managers_per_hour < 0 || values.min_managers_per_hour > 10) {
    return "Min managers per hour must be between 0 and 10.";
  }
  if (values.max_consecutive_shifts < 1 || values.max_consecutive_shifts > 7) {
    return "Max consecutive shifts must be between 1 and 7.";
  }
  if (values.min_hours_between_shifts < 0 || values.min_hours_between_shifts > 24) {
    return "Min hours between shifts must be between 0 and 24.";
  }
  if (values.min_managers_per_hour > values.min_staff_per_shift) {
    return "Min managers per hour cannot exceed min staff per shift.";
  }
  if (values.business_start_hour < 0 || values.business_start_hour > 23) {
    return "Business start hour must be between 0 and 23.";
  }
  if (values.business_end_hour < 1 || values.business_end_hour > 24) {
    return "Business end hour must be between 1 and 24.";
  }
  if (values.business_end_hour <= values.business_start_hour) {
    return "Business end hour must be later than business start hour.";
  }

  return null;
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
          setStatus(formatApiError(err, { fallbackMessage: "Failed to load workplace constraints." }));
          setStatusType("error");
        }
      }
    }

    loadConstraints();

    return () => {
      cancelled = true;
    };
  }, []);

  const updateConstraint = (
    field:
      | "min_staff_per_shift"
      | "min_managers_per_hour"
      | "max_consecutive_shifts"
      | "min_hours_between_shifts"
      | "business_start_hour"
      | "business_end_hour",
    value: number
  ) => {
    setConstraints(current => {
      if (!current) return current;
      return { ...current, [field]: value };
    });
  };

  const handleSave = async () => {
    if (!constraints) return;
    const validationError = validateConstraints(constraints);
    if (validationError) {
      setStatus(validationError);
      setStatusType("error");
      return;
    }

    setStatus("Saving workplace constraints...");
    setStatusType("loading");
    try {
      const response = await API.put<WorkplaceConstraintsResponse>("/workplace/constraints", {
        min_staff_per_shift: constraints.min_staff_per_shift,
        min_managers_per_hour: constraints.min_managers_per_hour,
        max_consecutive_shifts: constraints.max_consecutive_shifts,
        min_hours_between_shifts: constraints.min_hours_between_shifts,
        business_start_hour: constraints.business_start_hour,
        business_end_hour: constraints.business_end_hour,
      });
      setConstraints(response.data);
      setStatus("Constraints saved.");
      setStatusType("success");
    } catch (err: unknown) {
      console.error(err);
      setStatus(formatApiError(err, {
        fallbackMessage: "Failed to save workplace constraints.",
        detailMap: {
          "min_managers_per_hour cannot exceed min_staff_per_shift": "Min managers per hour cannot exceed min staff per shift.",
          "business_end_hour must be later than business_start_hour": "Business end hour must be later than business start hour.",
        },
      }));
      setStatusType("error");
    }
  };

  const startHourOptions = Array.from({ length: 24 }, (_, hour) => ({
    value: hour,
    label: `${String(hour).padStart(2, "0")}:00`,
  }));
  const endHourOptions = Array.from({ length: 24 }, (_, index) => {
    const hour = index + 1;
    return {
      value: hour,
      label: `${String(hour).padStart(2, "0")}:00`,
    };
  });

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

          <label className="workplace-constraints__field">
            <span>Max consecutive shifts</span>
            <input
              type="number"
              min={1}
              max={7}
              value={constraints?.max_consecutive_shifts ?? 5}
              onChange={event => updateConstraint("max_consecutive_shifts", Number(event.target.value))}
              disabled={!constraints || statusType === "loading"}
            />
          </label>

          <label className="workplace-constraints__field">
            <span>Min hours between shifts</span>
            <input
              type="number"
              min={0}
              max={24}
              value={constraints?.min_hours_between_shifts ?? 11}
              onChange={event => updateConstraint("min_hours_between_shifts", Number(event.target.value))}
              disabled={!constraints || statusType === "loading"}
            />
          </label>

          <label className="workplace-constraints__field">
            <span>Business start hour</span>
            <select
              value={constraints?.business_start_hour ?? 6}
              onChange={event => updateConstraint("business_start_hour", Number(event.target.value))}
              disabled={!constraints || statusType === "loading"}
            >
              {startHourOptions.map(option => (
                <option key={`start-${option.value}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <label className="workplace-constraints__field">
            <span>Business end hour</span>
            <select
              value={constraints?.business_end_hour ?? 22}
              onChange={event => updateConstraint("business_end_hour", Number(event.target.value))}
              disabled={!constraints || statusType === "loading"}
            >
              {endHourOptions.map(option => (
                <option key={`end-${option.value}`} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
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

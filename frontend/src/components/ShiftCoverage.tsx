import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/api";
import "./ShiftCoverage.css";

type CoverageStatus = "fully_staffed" | "understaffed";

interface HourCoverage {
  hour_start: string;
  hour_end: string;
  required_staff: number;
  assigned_staff: number;
  status: CoverageStatus;
}

interface DayCoverage {
  day_of_week: number;
  hours: HourCoverage[];
}

interface CoverageResponse {
  business_hours: {
    start: string;
    end: string;
  };
  minimum_staff_per_shift: number;
  summary: {
    fully_staffed_hours: number;
    understaffed_hours: number;
  };
  coverage: DayCoverage[];
}

interface ShiftCoverageProps {
  weekStartDate?: string;
}

const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function formatDayLabel(dayIndex: number, weekStartDate?: string) {
  if (!weekStartDate) return days[dayIndex];
  const [year, month, day] = weekStartDate.split("-").map(Number);
  const baseDate = new Date(year, month - 1, day);
  baseDate.setDate(baseDate.getDate() + dayIndex);
  const mm = String(baseDate.getMonth() + 1).padStart(2, "0");
  const dd = String(baseDate.getDate()).padStart(2, "0");
  return `${days[dayIndex]} ${dd}/${mm}`;
}

function formatHourLabel(hourStr: string) {
  const [hourRaw] = hourStr.split(":");
  const hour = Number(hourRaw);
  const suffix = hour >= 12 ? "PM" : "AM";
  const hour12 = hour % 12 || 12;
  return `${hour12}:00 ${suffix}`;
}

function statusLabel(status: CoverageStatus) {
  if (status === "fully_staffed") return "Fully staffed";
  return "Understaffed";
}

export default function ShiftCoverage({ weekStartDate }: ShiftCoverageProps) {
  const [data, setData] = useState<CoverageResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const loadCoverage = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await API.get<CoverageResponse>(
        "/roster/coverage",
        weekStartDate ? { params: { week_start_date: weekStartDate } } : undefined
      );
      setData(response.data);
    } catch (err) {
      console.error(err);
      setError("Failed to load shift coverage.");
    } finally {
      setLoading(false);
    }
  }, [weekStartDate]);

  useEffect(() => {
    loadCoverage();
  }, [loadCoverage]);

  const dayCards = useMemo(() => {
    if (!data) {
      return [];
    }

    return [...data.coverage]
      .sort((a, b) => a.day_of_week - b.day_of_week)
      .map(day => {
        const totals = day.hours.reduce(
          (acc, hour) => {
            if (hour.status === "fully_staffed") acc.fully += 1;
            if (hour.status === "understaffed") acc.under += 1;
            return acc;
          },
          { fully: 0, under: 0 }
        );

        return {
          ...day,
          totals,
        };
      });
  }, [data]);

  const totalHours = useMemo(() => {
    if (!data) return 0;
    return data.summary.fully_staffed_hours + data.summary.understaffed_hours;
  }, [data]);

  const coverageRate = useMemo(() => {
    if (totalHours === 0 || !data) return 0;
    return Math.round((data.summary.fully_staffed_hours / totalHours) * 100);
  }, [data, totalHours]);

  return (
    <section className="coverage" aria-label="Shift coverage by day and hour">
      <header className="coverage__header">
        <div className="coverage__title-wrap">
          <p className="coverage__eyebrow">Coverage Monitor</p>
          <h2>Shift Coverage</h2>
          <p>Track staffing health by day and hour with clear gaps highlighted.</p>
        </div>
        <button type="button" className="coverage__refresh" onClick={loadCoverage} disabled={loading}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      {loading ? <p className="coverage__state">Loading coverage...</p> : null}
      {!loading && error ? <p className="coverage__state coverage__state--error">{error}</p> : null}

      {!loading && !error && data ? (
        <>
          <div className="coverage__stats-grid">
            <article className="coverage__stat-card">
              <p>Coverage Rate</p>
              <strong>{coverageRate}%</strong>
            </article>
            <article className="coverage__stat-card">
              <p>Fully Staffed Hours</p>
              <strong>{data.summary.fully_staffed_hours}</strong>
            </article>
            <article className="coverage__stat-card">
              <p>Understaffed Hours</p>
              <strong>{data.summary.understaffed_hours}</strong>
            </article>
            <article className="coverage__stat-card">
              <p>Total Evaluated Hours</p>
              <strong>{totalHours}</strong>
            </article>
          </div>

          <p className="coverage__meta">
            Business hours: {formatHourLabel(data.business_hours.start)} to {formatHourLabel(data.business_hours.end)}.
            Minimum staff per shift: {data.minimum_staff_per_shift}.
          </p>

          <div className="coverage__legend" aria-label="Coverage legend">
            <span className="coverage__legend-item coverage__legend-item--fully_staffed">Fully staffed</span>
            <span className="coverage__legend-item coverage__legend-item--understaffed">Understaffed</span>
          </div>

          <div className="coverage__days">
            {dayCards.map(day => (
              <article key={day.day_of_week} className="coverage__day-card">
                <header className="coverage__day-header">
                  <h3>{formatDayLabel(day.day_of_week, weekStartDate)}</h3>
                  <p>
                    {day.totals.under} understaffed, {day.totals.fully} fully staffed
                  </p>
                </header>

                <div className="coverage__strip" role="list" aria-label={`${formatDayLabel(day.day_of_week, weekStartDate)} hourly coverage`}>
                  {day.hours.map(hour => (
                    <div
                      key={`${day.day_of_week}-${hour.hour_start}`}
                      role="listitem"
                      className={`coverage__block coverage__block--${hour.status}`}
                      title={`${formatDayLabel(day.day_of_week, weekStartDate)} ${formatHourLabel(hour.hour_start)}-${formatHourLabel(hour.hour_end)}: ${statusLabel(hour.status)} (${hour.assigned_staff}/${hour.required_staff} staff)`}
                    >
                      <span>{formatHourLabel(hour.hour_start)}</span>
                      <small>{hour.assigned_staff}/{hour.required_staff}</small>
                    </div>
                  ))}
                </div>
              </article>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}


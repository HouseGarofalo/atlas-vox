import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Gauge,
  History,
  Mic,
  ThumbsDown,
  ThumbsUp,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import { Card } from "../components/ui/Card";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { api } from "../services/api";
import { createLogger } from "../utils/logger";
import type { QualityDashboardResponse, QualityWerPoint } from "../types";

const logger = createLogger("QualityDashboardPage");

/**
 * VQ-36 — per-profile quality dashboard.
 *
 * Aggregates everything the SL-25/SL-27/SL-28 + audio-quality tracks
 * emit and renders a single-glance health picture: overall score,
 * WER trend, per-version metrics, thumbs distribution, sample health.
 * Charts are inline SVG sparklines so we don't pull a charting dependency
 * on this first pass.
 */
export default function QualityDashboardPage() {
  const { id: profileId } = useParams<{ id: string }>();
  const [data, setData] = useState<QualityDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!profileId) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .getQualityDashboard(profileId)
      .then((res) => {
        if (cancelled) return;
        setData(res);
        logger.info("quality_dashboard_loaded", {
          profile_id: profileId,
          overall: res.overall_score,
          versions: res.version_metrics.length,
        });
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load dashboard");
      })
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [profileId]);

  if (!profileId) {
    return <p className="p-6 text-sm text-[var(--color-text-secondary)]">Missing profile id.</p>;
  }

  if (loading) {
    return (
      <div className="p-6 space-y-3">
        <div className="h-8 w-64 rounded bg-[var(--color-bg-secondary)] animate-pulse" />
        <div className="h-32 rounded bg-[var(--color-bg-secondary)] animate-pulse" />
        <div className="h-48 rounded bg-[var(--color-bg-secondary)] animate-pulse" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <div className="flex items-center gap-2 rounded border border-[var(--color-error-border)] bg-[var(--color-error-bg)] p-3 text-sm text-[var(--color-error)]">
          <AlertTriangle className="h-4 w-4" />
          <span>{error ?? "No data available"}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen p-6 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            Quality Dashboard
          </h1>
          <p className="text-sm text-[var(--color-text-secondary)]">
            {data.profile_name} · {data.synthesis_count} syntheses ·{" "}
            {data.version_metrics.length} version{data.version_metrics.length === 1 ? "" : "s"}
          </p>
        </div>
        <Link
          to={`/profiles`}
          className="text-sm text-[var(--color-text-secondary)] hover:text-[var(--color-text)] transition-colors"
        >
          ← All profiles
        </Link>
      </header>

      {data.warnings.length > 0 && (
        <div className="rounded border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] p-3 text-xs text-[var(--color-warning)]">
          <div className="flex items-center gap-2 font-medium mb-1">
            <AlertTriangle className="h-3.5 w-3.5" /> Incomplete data
          </div>
          <ul className="list-disc list-inside space-y-0.5">
            {data.warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <KpiCard
          icon={<Gauge className="h-5 w-5" />}
          label="Overall Score"
          value={`${data.overall_score.toFixed(0)}`}
          suffix=" / 100"
          tone={scoreTone(data.overall_score)}
        />
        <KpiCard
          icon={<Activity className="h-5 w-5" />}
          label="Recent WER"
          value={data.recent_wer != null ? `${(data.recent_wer * 100).toFixed(1)}%` : "—"}
          tone={data.recent_wer == null ? "muted" : werTone(data.recent_wer)}
        />
        <KpiCard
          icon={<ThumbsUp className="h-5 w-5" />}
          label="User Approval"
          value={
            data.rating_distribution.total > 0
              ? `${data.rating_distribution.up_pct.toFixed(0)}%`
              : "—"
          }
          suffix={
            data.rating_distribution.total > 0
              ? ` · ${data.rating_distribution.total} ratings`
              : undefined
          }
          tone={
            data.rating_distribution.total === 0
              ? "muted"
              : data.rating_distribution.up_pct >= 70
                ? "good"
                : data.rating_distribution.up_pct >= 40
                  ? "warn"
                  : "bad"
          }
        />
        <KpiCard
          icon={<Mic className="h-5 w-5" />}
          label="Sample Health"
          value={
            data.sample_health.total > 0
              ? `${data.sample_health.pass_rate_pct.toFixed(0)}%`
              : "—"
          }
          suffix={
            data.sample_health.total > 0
              ? ` · ${data.sample_health.passed}/${data.sample_health.passed + data.sample_health.failed} pass`
              : undefined
          }
          tone={
            data.sample_health.total === 0
              ? "muted"
              : data.sample_health.pass_rate_pct >= 80
                ? "good"
                : data.sample_health.pass_rate_pct >= 50
                  ? "warn"
                  : "bad"
          }
        />
      </div>

      {/* WER time series */}
      <CollapsiblePanel
        title="Synthesis WER Over Time"
        icon={<TrendingDown className="h-4 w-4 text-electric-500" />}
        defaultOpen
      >
        <WerSparkline points={data.wer_series} />
      </CollapsiblePanel>

      {/* Version metrics table */}
      <CollapsiblePanel
        title="Version History"
        icon={<History className="h-4 w-4 text-primary-500" />}
        defaultOpen={data.version_metrics.length > 0}
      >
        {data.version_metrics.length === 0 ? (
          <p className="text-sm text-[var(--color-text-secondary)]">
            No trained versions yet. Train the profile to populate this table.
          </p>
        ) : (
          <div
            data-testid="version-metrics-table"
            className="overflow-x-auto"
          >
            <table className="w-full text-sm">
              <thead className="text-xs uppercase text-[var(--color-text-secondary)]">
                <tr>
                  <th className="px-2 py-1 text-left">#</th>
                  <th className="px-2 py-1 text-left">Created</th>
                  <th className="px-2 py-1 text-left">Method</th>
                  <th className="px-2 py-1 text-right">WER</th>
                  <th className="px-2 py-1 text-right">MOS</th>
                  <th className="px-2 py-1 text-right">Similarity</th>
                  <th className="px-2 py-1 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {data.version_metrics.map((v) => (
                  <tr
                    key={v.version_id}
                    className={`border-t border-[var(--color-border)] ${
                      v.is_active ? "bg-[var(--color-hover)]" : ""
                    }`}
                  >
                    <td className="px-2 py-1 font-medium">v{v.version_number}</td>
                    <td className="px-2 py-1 text-xs text-[var(--color-text-secondary)]">
                      {new Date(v.created_at).toLocaleString()}
                    </td>
                    <td className="px-2 py-1 text-xs">{v.method ?? "—"}</td>
                    <td className="px-2 py-1 text-right font-mono">
                      {v.quality_wer != null ? `${(v.quality_wer * 100).toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-2 py-1 text-right font-mono">
                      {v.mos != null ? v.mos.toFixed(2) : "—"}
                    </td>
                    <td className="px-2 py-1 text-right font-mono">
                      {v.speaker_similarity != null
                        ? `${(v.speaker_similarity * 100).toFixed(0)}%`
                        : "—"}
                    </td>
                    <td className="px-2 py-1">
                      <div className="flex items-center gap-1 text-xs">
                        {v.is_active && (
                          <span className="rounded-full bg-[var(--color-success-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-success)]">
                            Active
                          </span>
                        )}
                        {v.is_regression === true && (
                          <span className="rounded-full bg-[var(--color-warning-bg)] px-2 py-0.5 text-[10px] font-medium text-[var(--color-warning)] flex items-center gap-1">
                            <TrendingUp className="h-3 w-3" />
                            Regression
                          </span>
                        )}
                        {v.is_regression === false && (
                          <CheckCircle2 className="h-3.5 w-3.5 text-[var(--color-success)]" />
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>

      {/* Ratings + sample health side-by-side */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <ThumbsUp className="h-4 w-4 text-electric-500" /> User Ratings
          </h3>
          {data.rating_distribution.total === 0 ? (
            <p className="text-xs text-[var(--color-text-secondary)]">
              No feedback received yet. Enable thumbs-up/down on synthesis history to populate this.
            </p>
          ) : (
            <>
              <div className="flex items-center gap-3 text-sm">
                <span className="flex items-center gap-1 text-green-500">
                  <ThumbsUp className="h-3.5 w-3.5" />
                  {data.rating_distribution.up}
                </span>
                <span className="flex items-center gap-1 text-red-500">
                  <ThumbsDown className="h-3.5 w-3.5" />
                  {data.rating_distribution.down}
                </span>
                <span className="text-xs text-[var(--color-text-secondary)]">
                  · {data.rating_distribution.total} total
                </span>
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
                <div
                  className="h-full bg-green-500 transition-all"
                  style={{ width: `${data.rating_distribution.up_pct}%` }}
                />
              </div>
            </>
          )}
        </Card>

        <Card>
          <h3 className="text-sm font-semibold mb-2 flex items-center gap-2">
            <Mic className="h-4 w-4 text-primary-500" /> Training Sample Health
          </h3>
          {data.sample_health.total === 0 ? (
            <p className="text-xs text-[var(--color-text-secondary)]">
              No samples uploaded yet.
            </p>
          ) : (
            <>
              <div className="flex items-center gap-3 text-sm">
                <span className="flex items-center gap-1 text-green-500">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                  {data.sample_health.passed} pass
                </span>
                <span className="flex items-center gap-1 text-red-500">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  {data.sample_health.failed} fail
                </span>
                {data.sample_health.unknown > 0 && (
                  <span className="text-xs text-[var(--color-text-secondary)]">
                    {data.sample_health.unknown} unanalyzed
                  </span>
                )}
              </div>
              <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-[var(--color-bg-secondary)]">
                <div
                  className="h-full bg-green-500 transition-all"
                  style={{ width: `${data.sample_health.pass_rate_pct}%` }}
                />
              </div>
            </>
          )}
        </Card>
      </div>
    </div>
  );
}

/* --- Internal components --- */

type Tone = "good" | "warn" | "bad" | "muted";

function scoreTone(score: number): Tone {
  if (score >= 75) return "good";
  if (score >= 50) return "warn";
  if (score > 0) return "bad";
  return "muted";
}

function werTone(wer: number): Tone {
  if (wer <= 0.1) return "good";
  if (wer <= 0.3) return "warn";
  return "bad";
}

function KpiCard({
  icon,
  label,
  value,
  suffix,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  suffix?: string;
  tone: Tone;
}) {
  const toneClass = {
    good: "text-[var(--color-success)]",
    warn: "text-[var(--color-warning)]",
    bad: "text-[var(--color-error)]",
    muted: "text-[var(--color-text-tertiary)]",
  }[tone];
  return (
    <Card>
      <div className="flex items-center gap-3">
        <div className={toneClass}>{icon}</div>
        <div className="flex-1">
          <div className="text-xs text-[var(--color-text-secondary)]">{label}</div>
          <div className={`text-2xl font-display font-bold ${toneClass}`}>
            {value}
            {suffix && (
              <span className="text-sm font-normal text-[var(--color-text-secondary)]">
                {suffix}
              </span>
            )}
          </div>
        </div>
      </div>
    </Card>
  );
}

/**
 * Tiny inline SVG sparkline for WER over time. Avoids pulling in a
 * charting library on a page that renders once per profile.
 */
function WerSparkline({ points }: { points: QualityWerPoint[] }) {
  const { path, area, yLabels, count } = useMemo(() => {
    if (points.length === 0) {
      return { path: "", area: "", yLabels: [] as string[], count: 0 };
    }
    const width = 600;
    const height = 140;
    const pad = { top: 10, right: 16, bottom: 22, left: 40 };
    const xStep = (width - pad.left - pad.right) / Math.max(points.length - 1, 1);
    const yMin = 0;
    const yMax = Math.max(0.4, ...points.map((p) => p.quality_wer));
    const scaleY = (v: number) =>
      pad.top + (1 - (v - yMin) / (yMax - yMin)) * (height - pad.top - pad.bottom);
    const xyPath = points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${pad.left + i * xStep} ${scaleY(p.quality_wer)}`)
      .join(" ");
    const baseY = height - pad.bottom;
    const areaPath =
      `${xyPath} L ${pad.left + (points.length - 1) * xStep} ${baseY} L ${pad.left} ${baseY} Z`;
    const yLabels = [yMin, yMax / 2, yMax].map((v) => `${(v * 100).toFixed(0)}%`);
    return { path: xyPath, area: areaPath, yLabels, count: points.length };
  }, [points]);

  if (count === 0) {
    return (
      <p className="text-sm text-[var(--color-text-secondary)]">
        No Whisper-check data yet. Once the SL-28 verification task processes new
        syntheses, WER will chart here.
      </p>
    );
  }

  return (
    <div className="w-full overflow-x-auto">
      <svg
        data-testid="wer-sparkline"
        viewBox="0 0 600 140"
        className="w-full max-w-3xl h-40 text-electric-500"
        aria-label={`Word error rate over the last ${count} syntheses`}
      >
        <path d={area} fill="currentColor" fillOpacity="0.1" />
        <path d={path} fill="none" stroke="currentColor" strokeWidth="2" />
        {yLabels.map((label, i) => (
          <text
            key={label}
            x={6}
            y={10 + (140 - 32) * (1 - i / 2)}
            fontSize="10"
            fill="currentColor"
            opacity="0.5"
          >
            {label}
          </text>
        ))}
      </svg>
      <p className="mt-1 text-xs text-[var(--color-text-secondary)]">
        Oldest → newest · lower is better
      </p>
    </div>
  );
}

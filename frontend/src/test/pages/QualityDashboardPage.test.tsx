import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import QualityDashboardPage from "../../pages/QualityDashboardPage";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

const getQualityDashboard = vi.fn();
vi.mock("../../services/api", () => ({
  api: {
    getQualityDashboard: (...args: unknown[]) => getQualityDashboard(...args),
  },
}));

function renderAtProfile(id: string) {
  return render(
    <MemoryRouter initialEntries={[`/profiles/${id}/quality`]}>
      <Routes>
        <Route path="/profiles/:id/quality" element={<QualityDashboardPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

function mockDashboard(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    profile_id: "p-1",
    profile_name: "Test Voice",
    generated_at: "2026-04-18T12:00:00Z",
    overall_score: 82.5,
    recent_wer: 0.08,
    active_version_id: "v-2",
    wer_series: [
      { history_id: "h1", created_at: "2026-04-10T12:00:00Z", quality_wer: 0.12 },
      { history_id: "h2", created_at: "2026-04-12T12:00:00Z", quality_wer: 0.09 },
      { history_id: "h3", created_at: "2026-04-15T12:00:00Z", quality_wer: 0.08 },
    ],
    version_metrics: [
      {
        version_id: "v-1",
        version_number: 1,
        created_at: "2026-04-01T12:00:00Z",
        quality_wer: 0.15,
        mos: 3.5,
        speaker_similarity: null,
        is_regression: null,
        method: "clone",
        is_active: false,
      },
      {
        version_id: "v-2",
        version_number: 2,
        created_at: "2026-04-10T12:00:00Z",
        quality_wer: 0.08,
        mos: 4.1,
        speaker_similarity: 0.92,
        is_regression: false,
        method: "clone",
        is_active: true,
      },
    ],
    rating_distribution: { up: 8, down: 2, total: 10, up_pct: 80 },
    sample_health: { total: 6, passed: 5, failed: 1, unknown: 0, pass_rate_pct: 83.3 },
    synthesis_count: 42,
    warnings: [],
    ...overrides,
  };
}

describe("QualityDashboardPage", () => {
  beforeEach(() => {
    getQualityDashboard.mockReset();
  });

  it("renders the KPI row, WER sparkline, and version table from the payload", async () => {
    getQualityDashboard.mockResolvedValueOnce(mockDashboard());
    renderAtProfile("p-1");

    await waitFor(() => expect(getQualityDashboard).toHaveBeenCalledWith("p-1"));

    // Header identifies the profile.
    expect(await screen.findByText("Test Voice", { exact: false })).toBeInTheDocument();

    // KPIs include the overall score and recent WER formatted as a percentage.
    // Use a flexible matcher because the score value is split across the
    // numeric span and its " / 100" suffix.
    expect(
      screen.getByText((_content, el) => el?.textContent === "83 / 100"),
    ).toBeInTheDocument();
    // "8.0%" appears in both the recent-WER KPI and the v2 metrics row.
    expect(screen.getAllByText("8.0%").length).toBeGreaterThanOrEqual(1);

    // WER sparkline SVG renders.
    expect(screen.getByTestId("wer-sparkline")).toBeInTheDocument();

    // Version table lists both versions with the active pill on v2.
    const table = screen.getByTestId("version-metrics-table");
    expect(table).toHaveTextContent("v1");
    expect(table).toHaveTextContent("v2");
    expect(table).toHaveTextContent("Active");
  });

  it("shows a friendly empty state when there's no WER data yet", async () => {
    getQualityDashboard.mockResolvedValueOnce(
      mockDashboard({ wer_series: [], warnings: ["no Whisper-check data yet"] }),
    );
    renderAtProfile("p-42");
    await waitFor(() => expect(getQualityDashboard).toHaveBeenCalled());

    // Both the warnings banner AND the empty-chart fallback mention
    // "Whisper-check" so we expect multiple matches — this is intentional
    // (banner summarises, body explains next step).
    const mentions = await screen.findAllByText(/Whisper-check/i);
    expect(mentions.length).toBeGreaterThanOrEqual(2);
    // The warnings banner is rendered.
    expect(screen.getByText(/Incomplete data/i)).toBeInTheDocument();
  });

  it("surfaces the API error when the dashboard fetch fails", async () => {
    getQualityDashboard.mockRejectedValueOnce(new Error("profile missing"));
    renderAtProfile("missing");
    await waitFor(() =>
      expect(screen.getByText(/profile missing/i)).toBeInTheDocument(),
    );
  });

  it("handles the zero-ratings / zero-samples empty-state cleanly", async () => {
    getQualityDashboard.mockResolvedValueOnce(
      mockDashboard({
        rating_distribution: { up: 0, down: 0, total: 0, up_pct: 0 },
        sample_health: { total: 0, passed: 0, failed: 0, unknown: 0, pass_rate_pct: 0 },
      }),
    );
    renderAtProfile("p-quiet");
    await waitFor(() => expect(getQualityDashboard).toHaveBeenCalled());
    expect(await screen.findByText(/No feedback received yet/i)).toBeInTheDocument();
    expect(screen.getByText(/No samples uploaded yet/i)).toBeInTheDocument();
  });
});

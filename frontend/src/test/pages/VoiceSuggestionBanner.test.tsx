import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { VoiceSuggestionBanner } from "../../pages/synthesis/VoiceSuggestionBanner";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

const recommendVoice = vi.fn();
vi.mock("../../services/api", () => ({
  api: {
    recommendVoice: (...args: unknown[]) => recommendVoice(...args),
  },
}));

function mockRecommendation(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    text_excerpt: "Once upon a time...",
    top_context: "narrative",
    context_scores: [],
    recommendations: [
      {
        profile_id: "p-narrator",
        profile_name: "The Narrator",
        provider_name: "elevenlabs",
        voice_id: "v1",
        score: 0.92,
        reasons: ["elevenlabs affinity for 'narrative' = 0.85"],
      },
    ],
    ...overrides,
  };
}

describe("VoiceSuggestionBanner", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    recommendVoice.mockReset();
  });

  it("stays hidden for very short text", async () => {
    render(
      <VoiceSuggestionBanner text="Hi" currentProfileId="" onAccept={() => {}} />,
    );
    vi.advanceTimersByTime(1000);
    expect(screen.queryByTestId("voice-suggestion-banner")).toBeNull();
    expect(recommendVoice).not.toHaveBeenCalled();
  });

  it("debounces — rapid text changes result in a single fetch", async () => {
    recommendVoice.mockResolvedValue(mockRecommendation());
    const { rerender } = render(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom..."
        currentProfileId=""
        onAccept={() => {}}
      />,
    );
    // Keep editing for 300ms — no fetch yet.
    vi.advanceTimersByTime(300);
    rerender(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom long ago."
        currentProfileId=""
        onAccept={() => {}}
      />,
    );
    vi.advanceTimersByTime(300);
    expect(recommendVoice).not.toHaveBeenCalled();

    // User stops typing — after another 500ms the fetch fires ONCE.
    vi.advanceTimersByTime(600);
    expect(recommendVoice).toHaveBeenCalledTimes(1);
  });

  it("renders the suggestion after the debounce resolves", async () => {
    vi.useRealTimers();
    recommendVoice.mockResolvedValue(mockRecommendation());
    render(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom long ago — she listened to the silence."
        currentProfileId=""
        onAccept={() => {}}
      />,
    );
    await waitFor(() =>
      expect(screen.getByTestId("voice-suggestion-banner")).toBeInTheDocument(),
    );
    expect(screen.getByText(/Atlas suggests/i)).toBeInTheDocument();
    expect(screen.getByText(/The Narrator/i)).toBeInTheDocument();
    expect(screen.getByText(/narrative text/i)).toBeInTheDocument();
  });

  it("hides when user is already on the top suggestion", async () => {
    vi.useRealTimers();
    recommendVoice.mockResolvedValue(mockRecommendation());
    render(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom long ago — she listened to the silence."
        currentProfileId="p-narrator"
        onAccept={() => {}}
      />,
    );
    await waitFor(() => expect(recommendVoice).toHaveBeenCalled());
    // Banner should NOT appear — user already has it selected.
    expect(screen.queryByTestId("voice-suggestion-banner")).toBeNull();
  });

  it("accepts the suggestion and fires onAccept with the profile id", async () => {
    vi.useRealTimers();
    recommendVoice.mockResolvedValue(mockRecommendation());
    const onAccept = vi.fn();
    render(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom long ago — she listened to the silence."
        currentProfileId=""
        onAccept={onAccept}
      />,
    );
    await waitFor(() => expect(recommendVoice).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByText(/The Narrator/i)).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /use it/i }));
    expect(onAccept).toHaveBeenCalledWith("p-narrator");
  });

  it("can be dismissed and stays dismissed for that suggestion", async () => {
    vi.useRealTimers();
    recommendVoice.mockResolvedValue(mockRecommendation());
    render(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom long ago — she listened to the silence."
        currentProfileId=""
        onAccept={() => {}}
      />,
    );
    await waitFor(() => expect(recommendVoice).toHaveBeenCalled());
    await waitFor(() =>
      expect(screen.getByTestId("voice-suggestion-banner")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByRole("button", { name: /dismiss suggestion/i }));
    expect(screen.queryByTestId("voice-suggestion-banner")).toBeNull();
  });

  it("silently absorbs API failures", async () => {
    vi.useRealTimers();
    recommendVoice.mockRejectedValue(new Error("network down"));
    render(
      <VoiceSuggestionBanner
        text="Once upon a time in a quiet kingdom long ago — she listened to the silence."
        currentProfileId=""
        onAccept={() => {}}
      />,
    );
    await waitFor(() => expect(recommendVoice).toHaveBeenCalled());
    // No banner appears and no exception crashes the page.
    expect(screen.queryByTestId("voice-suggestion-banner")).toBeNull();
  });
});

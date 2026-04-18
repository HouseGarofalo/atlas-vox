import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProsodyPreview } from "../../pages/synthesis/ProsodyPreview";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({ debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() }),
}));

const prosodyPreview = vi.fn();
vi.mock("../../services/api", () => ({
  api: {
    prosodyPreview: (...args: unknown[]) => prosodyPreview(...args),
  },
}));

function mockResponse(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    text: "Hello there friend",
    emotion: null,
    words: [
      {
        index: 0, text: "Hello", pitch: 0.05, energy: 0.55, duration_ms: 110,
        syllables: 2, is_sentence_end: false, emphasis: "normal", reasons: [],
      },
      {
        index: 1, text: "there", pitch: -0.01, energy: 0.5, duration_ms: 55,
        syllables: 1, is_sentence_end: false, emphasis: "normal", reasons: [],
      },
      {
        index: 2, text: "friend", pitch: -0.05, energy: 0.5, duration_ms: 55,
        syllables: 1, is_sentence_end: true, emphasis: "normal", reasons: [],
      },
    ],
    sentence_count: 1,
    total_duration_ms: 220,
    pitch_min: -0.05,
    pitch_max: 0.05,
    ssml: '<speak>Hello there friend</speak>',
    supported_emotions: ["neutral", "cheerful", "sad", "excited"],
    ...overrides,
  };
}

describe("ProsodyPreview", () => {
  beforeEach(() => {
    prosodyPreview.mockReset();
  });

  it("renders nothing when text is empty", () => {
    render(<ProsodyPreview text="" />);
    expect(screen.queryByTestId("prosody-preview")).toBeNull();
    expect(prosodyPreview).not.toHaveBeenCalled();
  });

  it("fetches the preview after debounce and renders the sparkline + timeline", async () => {
    prosodyPreview.mockResolvedValueOnce(mockResponse());
    render(<ProsodyPreview text="Hello there friend" />);

    await waitFor(() => expect(prosodyPreview).toHaveBeenCalledTimes(1));

    expect(await screen.findByTestId("prosody-preview")).toBeInTheDocument();
    expect(screen.getByTestId("prosody-sparkline")).toBeInTheDocument();
    const timeline = screen.getByTestId("prosody-word-timeline");
    expect(timeline).toHaveTextContent("Hello");
    expect(timeline).toHaveTextContent("there");
    expect(timeline).toHaveTextContent("friend");
    expect(screen.getByText(/3 words/i)).toBeInTheDocument();
    // Duration surfaced in seconds.
    expect(screen.getByText(/0\.2s predicted/)).toBeInTheDocument();
  });

  it("cycles emphasis and re-fetches the preview", async () => {
    prosodyPreview.mockResolvedValue(mockResponse());
    render(<ProsodyPreview text="Hello there friend" />);

    await waitFor(() => expect(prosodyPreview).toHaveBeenCalledTimes(1));
    await screen.findByTestId("prosody-word-timeline");

    const helloBtn = screen.getByRole("button", { name: /Hello/ });
    await userEvent.click(helloBtn);

    // A second call should fire with the updated emphasis override.
    await waitFor(() => expect(prosodyPreview).toHaveBeenCalledTimes(2));
    const secondCallArgs = prosodyPreview.mock.calls[1];
    expect(secondCallArgs[0]).toBe("Hello there friend");
    expect(secondCallArgs[1].emphasis).toEqual({ 0: "strong" });
  });

  it("emits onSsmlChange with the latest SSML", async () => {
    prosodyPreview.mockResolvedValueOnce(mockResponse({ ssml: "<speak>abc</speak>" }));
    const onSsmlChange = vi.fn();
    render(<ProsodyPreview text="Hello there friend" onSsmlChange={onSsmlChange} />);
    await waitFor(() =>
      expect(onSsmlChange).toHaveBeenCalledWith("<speak>abc</speak>"),
    );
  });

  it("renders the emotion selector and fires onEmotionChange when changed", async () => {
    prosodyPreview.mockResolvedValue(mockResponse());
    const onEmotionChange = vi.fn();
    render(
      <ProsodyPreview
        text="Hello there friend"
        emotion={null}
        onEmotionChange={onEmotionChange}
      />,
    );
    // Wait for the emotion dropdown itself to appear — it only renders
    // once the preview resolves with a supported_emotions list.
    const select = await screen.findByRole("combobox");
    await userEvent.selectOptions(select, "cheerful");
    expect(onEmotionChange).toHaveBeenCalledWith("cheerful");
  });

  it("handles API errors without crashing", async () => {
    prosodyPreview.mockRejectedValueOnce(new Error("network down"));
    render(<ProsodyPreview text="Hello there friend" />);
    await waitFor(() => expect(prosodyPreview).toHaveBeenCalled());
    // Error message surfaces in the panel header area.
    expect(await screen.findByText(/network down/i)).toBeInTheDocument();
  });
});

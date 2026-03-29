import { describe, it, expect, beforeEach, vi } from "vitest";
import { useTrainingStore } from "../../stores/trainingStore";

vi.mock("../../utils/logger", () => ({
  createLogger: () => ({
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  }),
}));

vi.mock("../../services/api", () => ({
  api: {
    listTrainingJobs: vi.fn(),
    startTraining: vi.fn(),
    cancelTrainingJob: vi.fn(),
    getTrainingJob: vi.fn(),
  },
}));

import { api } from "../../services/api";

const mockApi = vi.mocked(api);

describe("TrainingStore", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useTrainingStore.setState({
      jobs: [],
      loading: false,
      error: null,
    });
  });

  describe("fetchJobs", () => {
    it("fetches jobs successfully", async () => {
      const jobs = [
        { id: "j1", profile_id: "p1", status: "completed" },
        { id: "j2", profile_id: "p2", status: "training" },
      ];
      mockApi.listTrainingJobs.mockResolvedValue({ jobs, count: 2 } as any);

      await useTrainingStore.getState().fetchJobs();

      const state = useTrainingStore.getState();
      expect(state.jobs).toEqual(jobs);
      expect(state.loading).toBe(false);
      expect(state.error).toBeNull();
    });

    it("passes filter params", async () => {
      mockApi.listTrainingJobs.mockResolvedValue({ jobs: [], count: 0 } as any);

      await useTrainingStore.getState().fetchJobs({ profile_id: "p1", status: "training" });

      expect(mockApi.listTrainingJobs).toHaveBeenCalledWith({
        profile_id: "p1",
        status: "training",
      });
    });

    it("handles fetch errors", async () => {
      mockApi.listTrainingJobs.mockRejectedValue(new Error("Server error"));

      await useTrainingStore.getState().fetchJobs();

      const state = useTrainingStore.getState();
      expect(state.error).toBe("Server error");
      expect(state.loading).toBe(false);
    });
  });

  describe("startTraining", () => {
    it("starts training and adds job to list", async () => {
      const newJob = {
        id: "j3",
        profile_id: "p1",
        provider_name: "coqui_xtts",
        status: "queued",
      };
      mockApi.startTraining.mockResolvedValue(newJob as any);

      const result = await useTrainingStore.getState().startTraining("p1", {
        provider_name: "coqui_xtts",
      });

      expect(result).toEqual(newJob);
      expect(useTrainingStore.getState().jobs).toContainEqual(newJob);
    });

    it("prepends new job to list", async () => {
      useTrainingStore.setState({
        jobs: [{ id: "j1", status: "completed" } as any],
      });
      const newJob = { id: "j2", status: "queued" };
      mockApi.startTraining.mockResolvedValue(newJob as any);

      await useTrainingStore.getState().startTraining("p1");

      const jobs = useTrainingStore.getState().jobs;
      expect(jobs[0]).toEqual(newJob);
      expect(jobs).toHaveLength(2);
    });
  });

  describe("cancelJob", () => {
    it("cancels job and updates list", async () => {
      useTrainingStore.setState({
        jobs: [
          { id: "j1", status: "training" } as any,
          { id: "j2", status: "queued" } as any,
        ],
      });
      const cancelledJob = { id: "j1", status: "cancelled" };
      mockApi.cancelTrainingJob.mockResolvedValue(cancelledJob as any);

      await useTrainingStore.getState().cancelJob("j1");

      const job = useTrainingStore.getState().jobs.find((j) => j.id === "j1");
      expect(job?.status).toBe("cancelled");
    });
  });
});

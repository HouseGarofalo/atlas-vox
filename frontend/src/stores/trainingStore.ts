import { create } from "zustand";
import { api } from "../services/api";
import type { TrainingJob } from "../types";
import { createLogger } from "../utils/logger";
import { getErrorMessage } from "../utils/errors";

const logger = createLogger("TrainingStore");

interface TrainingState {
  jobs: TrainingJob[];
  loading: boolean;
  error: string | null;
  fetchJobs: (params?: { profile_id?: string; status?: string }) => Promise<void>;
  startTraining: (profileId: string, data?: { provider_name?: string; config?: Record<string, string> }) => Promise<TrainingJob>;
  cancelJob: (jobId: string) => Promise<void>;
  refreshJob: (jobId: string) => Promise<TrainingJob>;
}

export const useTrainingStore = create<TrainingState>((set) => ({
  jobs: [],
  loading: false,
  error: null,

  fetchJobs: async (params) => {
    logger.info("fetchJobs", { params });
    set({ loading: true, error: null });
    try {
      const { jobs } = await api.listTrainingJobs(params);
      logger.info("fetchJobs_success", { count: jobs.length });
      set({ jobs, loading: false });
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("fetchJobs_failed", { error: message });
      set({ error: message, loading: false });
    }
  },

  startTraining: async (profileId, data = {}) => {
    logger.info("startTraining", { profileId, provider: data.provider_name });
    try {
      const job = await api.startTraining(profileId, data);
      logger.info("startTraining_success", { jobId: job.id });
      set((s) => ({ jobs: [job, ...s.jobs], error: null }));
      return job;
    } catch (e: unknown) {
      const message = getErrorMessage(e);
      logger.error("startTraining_failed", { profileId, error: message });
      set({ error: message });
      throw e;
    }
  },

  cancelJob: async (jobId) => {
    logger.info("cancelJob", { jobId });
    const updated = await api.cancelTrainingJob(jobId);
    set((s) => ({ jobs: s.jobs.map((j) => (j.id === jobId ? updated : j)) }));
  },

  refreshJob: async (jobId) => {
    logger.info("refreshJob", { jobId });
    const job = await api.getTrainingJob(jobId);
    set((s) => ({ jobs: s.jobs.map((j) => (j.id === jobId ? { ...j, ...job } : j)) }));
    return job;
  },
}));

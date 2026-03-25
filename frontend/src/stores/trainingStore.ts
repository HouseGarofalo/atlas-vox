import { create } from "zustand";
import { api } from "../services/api";
import type { TrainingJob } from "../types";

interface TrainingState {
  jobs: TrainingJob[];
  loading: boolean;
  error: string | null;
  fetchJobs: (params?: { profile_id?: string; status?: string }) => Promise<void>;
  startTraining: (profileId: string, data?: { provider_name?: string; config?: Record<string, any> }) => Promise<TrainingJob>;
  cancelJob: (jobId: string) => Promise<void>;
  refreshJob: (jobId: string) => Promise<TrainingJob>;
}

export const useTrainingStore = create<TrainingState>((set) => ({
  jobs: [],
  loading: false,
  error: null,

  fetchJobs: async (params) => {
    set({ loading: true, error: null });
    try {
      const { jobs } = await api.listTrainingJobs(params);
      set({ jobs, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  startTraining: async (profileId, data = {}) => {
    const job = await api.startTraining(profileId, data);
    set((s) => ({ jobs: [job, ...s.jobs] }));
    return job;
  },

  cancelJob: async (jobId) => {
    const updated = await api.cancelTrainingJob(jobId);
    set((s) => ({ jobs: s.jobs.map((j) => (j.id === jobId ? updated : j)) }));
  },

  refreshJob: async (jobId) => {
    const job = await api.getTrainingJob(jobId);
    set((s) => ({ jobs: s.jobs.map((j) => (j.id === jobId ? { ...j, ...job } : j)) }));
    return job;
  },
}));

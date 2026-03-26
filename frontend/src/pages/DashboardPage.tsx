import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Mic, Activity, AudioLines, AlertCircle } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { useProfileStore } from "../stores/profileStore";
import { useTrainingStore } from "../stores/trainingStore";
import { useProviderStore } from "../stores/providerStore";
import { useSynthesisStore } from "../stores/synthesisStore";
import ProviderLogo from "../components/providers/ProviderLogo";

export default function DashboardPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { jobs, fetchJobs } = useTrainingStore();
  const { providers, fetchProviders, checkAllHealth } = useProviderStore();
  const { history, fetchHistory } = useSynthesisStore();

  useEffect(() => {
    fetchProfiles();
    fetchJobs();
    fetchProviders().then(() => checkAllHealth());
    fetchHistory(10);
  }, []);

  const activeJobs = jobs.filter((j) => ["queued", "training", "preprocessing"].includes(j.status));
  const readyProfiles = profiles.filter((p) => p.status === "ready").length;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card className="flex items-center gap-4">
          <div className="rounded-lg bg-primary-100 p-3 dark:bg-primary-900">
            <Mic className="h-6 w-6 text-primary-600 dark:text-primary-400" />
          </div>
          <div>
            <p className="text-2xl font-bold">{profiles.length}</p>
            <p className="text-sm text-[var(--color-text-secondary)]">Voice Profiles ({readyProfiles} ready)</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="rounded-lg bg-blue-100 p-3 dark:bg-blue-900">
            <Activity className="h-6 w-6 text-blue-600 dark:text-blue-400" />
          </div>
          <div>
            <p className="text-2xl font-bold">{activeJobs.length}</p>
            <p className="text-sm text-[var(--color-text-secondary)]">Active Training Jobs</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="rounded-lg bg-green-100 p-3 dark:bg-green-900">
            <AudioLines className="h-6 w-6 text-green-600 dark:text-green-400" />
          </div>
          <div>
            <p className="text-2xl font-bold">{history.length}</p>
            <p className="text-sm text-[var(--color-text-secondary)]">Recent Syntheses</p>
          </div>
        </Card>
        <Card className="flex items-center gap-4">
          <div className="rounded-lg bg-purple-100 p-3 dark:bg-purple-900">
            <AlertCircle className="h-6 w-6 text-purple-600 dark:text-purple-400" />
          </div>
          <div>
            <p className="text-2xl font-bold">{providers.filter((p) => p.enabled).length}</p>
            <p className="text-sm text-[var(--color-text-secondary)]">of {providers.length} Providers Active</p>
          </div>
        </Card>
      </div>

      {/* Provider health grid */}
      <Card>
        <h2 className="mb-3 text-lg font-semibold">Provider Health</h2>
        <div className="grid grid-cols-3 gap-2 sm:grid-cols-5 lg:grid-cols-9">
          {providers.map((p) => (
            <div key={p.name} className="flex flex-col items-center gap-1 rounded-lg border border-[var(--color-border)] p-2 text-center">
              <ProviderLogo name={p.name} size={22} />
              <span className="text-xs font-medium truncate w-full">{p.display_name}</span>
              <Badge status={p.health?.healthy ? "healthy" : p.enabled ? "unhealthy" : "pending"} />
            </div>
          ))}
        </div>
      </Card>

      {/* Active training jobs */}
      {activeJobs.length > 0 && (
        <Card>
          <h2 className="mb-3 text-lg font-semibold">Active Training Jobs</h2>
          <div className="space-y-2">
            {activeJobs.map((job) => (
              <div key={job.id} className="flex items-center justify-between rounded-lg border border-[var(--color-border)] p-3">
                <div>
                  <p className="text-sm font-medium">{job.profile_id.slice(0, 8)}...</p>
                  <p className="text-xs text-[var(--color-text-secondary)]">{job.provider_name}</p>
                </div>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 rounded-full bg-gray-200 dark:bg-gray-700">
                    <div className="h-full rounded-full bg-primary-500" style={{ width: `${job.progress * 100}%` }} />
                  </div>
                  <Badge status={job.status} />
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Recent synthesis history */}
      {history.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Recent Synthesis</h2>
            <Link to="/synthesis" className="text-sm text-primary-500 hover:underline">View all</Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                  <th className="pb-2 font-medium">Text</th>
                  <th className="pb-2 font-medium">Provider</th>
                  <th className="pb-2 font-medium">Latency</th>
                  <th className="pb-2 font-medium">Time</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 5).map((h: any) => (
                  <tr key={h.id} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="py-2 max-w-[200px] truncate">{h.text}</td>
                    <td className="py-2">{h.provider_name}</td>
                    <td className="py-2">{h.latency_ms}ms</td>
                    <td className="py-2 text-xs text-[var(--color-text-secondary)]">{new Date(h.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

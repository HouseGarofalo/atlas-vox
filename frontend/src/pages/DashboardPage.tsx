import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Mic, Activity, AudioLines, AlertCircle, Heart, Zap, Clock } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { useProfileStore } from "../stores/profileStore";
import { useTrainingStore } from "../stores/trainingStore";
import { useProviderStore } from "../stores/providerStore";
import { useSynthesisStore } from "../stores/synthesisStore";
import ProviderLogo from "../components/providers/ProviderLogo";
import { createLogger } from "../utils/logger";

const logger = createLogger("DashboardPage");

export default function DashboardPage() {
  const { profiles, fetchProfiles } = useProfileStore();
  const { jobs, fetchJobs } = useTrainingStore();
  const { providers, fetchProviders, checkAllHealth } = useProviderStore();
  const { history, fetchHistory } = useSynthesisStore();

  useEffect(() => {
    logger.info("page_mounted");
    Promise.all([
      fetchProfiles(),
      fetchJobs(),
      fetchProviders().then(() => checkAllHealth()),
      fetchHistory(10),
    ])
      .then(() => logger.info("data_fetch_complete"))
      .catch((err) => logger.error("data_fetch_error", { error: String(err) }));
  }, []);

  const activeJobs = jobs.filter((j) => ["queued", "training", "preprocessing"].includes(j.status));
  const readyProfiles = profiles.filter((p) => p.status === "ready").length;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      {/* Stats cards */}
      <CollapsiblePanel title="Overview" icon={<Zap className="h-4 w-4 text-primary-500" />}>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 lg:grid-cols-4">
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
      </CollapsiblePanel>

      {/* Provider health grid */}
      <CollapsiblePanel title="Provider Health" icon={<Heart className="h-4 w-4 text-red-500" />}>
        <div className="grid grid-cols-2 gap-2 xs:grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-9">
          {providers.map((p) => (
            <div key={p.name} className="flex flex-col items-center gap-1 rounded-lg border border-[var(--color-border)] p-2 text-center">
              <ProviderLogo name={p.name} size={22} />
              <span className="text-xs font-medium truncate w-full">{p.display_name}</span>
              <Badge status={p.health?.healthy ? "healthy" : p.enabled ? "unhealthy" : "pending"} />
            </div>
          ))}
        </div>
      </CollapsiblePanel>

      {/* Active training jobs */}
      {activeJobs.length > 0 && (
        <CollapsiblePanel title="Active Training Jobs" icon={<Activity className="h-4 w-4 text-blue-500" />} badge={<Badge status="training" />}>
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
        </CollapsiblePanel>
      )}

      {/* Recent synthesis history */}
      {history.length > 0 && (
        <CollapsiblePanel
          title="Recent Synthesis"
          icon={<Clock className="h-4 w-4 text-green-500" />}
          actions={<Link to="/synthesis" className="text-sm text-primary-500 hover:underline">View all</Link>}
        >
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                  <th className="pb-2 font-medium">Text</th>
                  <th className="pb-2 font-medium">Provider</th>
                  <th className="pb-2 font-medium hidden sm:table-cell">Latency</th>
                  <th className="pb-2 font-medium hidden sm:table-cell">Time</th>
                </tr>
              </thead>
              <tbody>
                {history.slice(0, 5).map((h: any) => (
                  <tr key={h.id} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="py-2 max-w-[200px] truncate">{h.text}</td>
                    <td className="py-2">{h.provider_name}</td>
                    <td className="py-2 hidden sm:table-cell">{h.latency_ms}ms</td>
                    <td className="py-2 text-xs text-[var(--color-text-secondary)] hidden sm:table-cell">{new Date(h.created_at).toLocaleTimeString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CollapsiblePanel>
      )}
    </div>
  );
}

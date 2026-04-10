import { useEffect } from "react";
import { Link } from "react-router-dom";
import { Mic, Activity, AudioLines, AlertCircle, Heart, Zap, Clock, TrendingUp } from "lucide-react";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import AudioReactiveBackground from "../components/audio/AudioReactiveBackground";
import VUMeter from "../components/audio/VUMeter";
import WaveformVisualizer from "../components/audio/WaveformVisualizer";
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
  const healthyProviders = providers.filter((p) => p.enabled && p.health?.healthy).length;

  return (
    <div className="relative min-h-screen">
      {/* Audio-reactive background */}
      <AudioReactiveBackground intensity="subtle" />

      <div className="relative z-10 space-y-8">
        {/* Studio Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-display font-bold text-gradient mb-2">
              Audio Control Center
            </h1>
            <p className="text-[var(--color-text-secondary)] font-medium">
              Real-time monitoring and voice synthesis command center
            </p>
          </div>

          {/* Master Level Display */}
          <Card variant="console" className="px-6 py-4">
            <div className="flex items-center gap-4">
              <div className="text-center">
                <div className="text-xs font-mono text-studio-silver mb-1">MASTER</div>
                <VUMeter level={85} barCount={8} height={24} />
              </div>
              <div className="text-center">
                <div className="text-xs font-mono text-studio-silver mb-1">OUTPUT</div>
                <div className="text-lg font-mono text-led-green">
                  {new Date().toLocaleTimeString()}
                </div>
              </div>
            </div>
          </Card>
        </div>

        {/* Main Stats Grid */}
        <CollapsiblePanel
          title="System Overview"
          icon={<Zap className="h-5 w-5 text-secondary-400" />}
          defaultOpen={true}
        >
          <div className="grid grid-cols-2 gap-6 lg:grid-cols-4">
            {/* Voice Profiles */}
            <Card variant="studio" className="group">
              <div className="flex items-center gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-primary-500/20 to-primary-600/30 group-hover:from-primary-500/30 group-hover:to-primary-600/40 transition-all duration-300">
                  <Mic className="h-8 w-8 text-primary-500" />
                </div>
                <div className="flex-1">
                  <p className="text-3xl font-display font-bold text-[var(--color-text)]">
                    {profiles.length}
                  </p>
                  <p className="text-sm text-[var(--color-text-secondary)] font-medium">
                    Voice Profiles
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-2 h-2 bg-led-green rounded-full" />
                    <span className="text-xs text-[var(--color-text-tertiary)]">
                      {readyProfiles} ready
                    </span>
                  </div>
                </div>
              </div>
              {/* Mini waveform */}
              <div className="mt-4">
                <WaveformVisualizer height={20} barCount={12} animated color="primary" />
              </div>
            </Card>

            {/* Active Training */}
            <Card variant="studio" className="group">
              <div className="flex items-center gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-electric-500/20 to-electric-600/30 group-hover:from-electric-500/30 group-hover:to-electric-600/40 transition-all duration-300">
                  <Activity className="h-8 w-8 text-electric-500" />
                </div>
                <div className="flex-1">
                  <p className="text-3xl font-display font-bold text-[var(--color-text)]">
                    {activeJobs.length}
                  </p>
                  <p className="text-sm text-[var(--color-text-secondary)] font-medium">
                    Training Jobs
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className={`w-2 h-2 rounded-full ${activeJobs.length > 0 ? 'bg-led-yellow animate-led-pulse' : 'bg-studio-slate'}`} />
                    <span className="text-xs text-[var(--color-text-tertiary)]">
                      {activeJobs.length > 0 ? 'Processing' : 'Idle'}
                    </span>
                  </div>
                </div>
              </div>
              {/* Training progress visualization */}
              <div className="mt-4">
                <WaveformVisualizer
                  height={20}
                  barCount={12}
                  animated={activeJobs.length > 0}
                  color="electric"
                />
              </div>
            </Card>

            {/* Synthesis Activity */}
            <Card variant="studio" className="group">
              <div className="flex items-center gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-secondary-400/20 to-secondary-500/30 group-hover:from-secondary-400/30 group-hover:to-secondary-500/40 transition-all duration-300">
                  <AudioLines className="h-8 w-8 text-secondary-500" />
                </div>
                <div className="flex-1">
                  <p className="text-3xl font-display font-bold text-[var(--color-text)]">
                    {history.length}
                  </p>
                  <p className="text-sm text-[var(--color-text-secondary)] font-medium">
                    Recent Syntheses
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-2 h-2 bg-led-green rounded-full" />
                    <span className="text-xs text-[var(--color-text-tertiary)]">
                      Last 24h
                    </span>
                  </div>
                </div>
              </div>
              <div className="mt-4">
                <WaveformVisualizer height={20} barCount={12} animated color="secondary" />
              </div>
            </Card>

            {/* Provider Health */}
            <Card variant="studio" className="group">
              <div className="flex items-center gap-4">
                <div className="p-4 rounded-xl bg-gradient-to-br from-green-500/20 to-emerald-600/30 group-hover:from-green-500/30 group-hover:to-emerald-600/40 transition-all duration-300">
                  <Heart className="h-8 w-8 text-green-500" />
                </div>
                <div className="flex-1">
                  <p className="text-3xl font-display font-bold text-[var(--color-text)]">
                    {healthyProviders}
                  </p>
                  <p className="text-sm text-[var(--color-text-secondary)] font-medium">
                    Healthy Providers
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <div className="w-2 h-2 bg-led-green rounded-full animate-led-pulse" />
                    <span className="text-xs text-[var(--color-text-tertiary)]">
                      of {providers.length} total
                    </span>
                  </div>
                </div>
              </div>
              <div className="mt-4 flex justify-center">
                <VUMeter level={healthyProviders / providers.length * 100} barCount={8} height={20} />
              </div>
            </Card>
          </div>
        </CollapsiblePanel>

        {/* Provider Health Console */}
        <CollapsiblePanel
          title="Provider Health Matrix"
          icon={<AlertCircle className="h-5 w-5 text-red-400" />}
          defaultOpen={true}
        >
          <Card variant="console" className="p-6">
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-9 gap-4">
              {providers.map((provider) => {
                const isHealthy = provider.health?.healthy;
                const isEnabled = provider.enabled;

                return (
                  <div
                    key={provider.name}
                    className="flex flex-col items-center gap-3 p-4 rounded-xl border border-studio-slate/30 bg-studio-charcoal/30 hover:bg-studio-charcoal/50 transition-all duration-300"
                  >
                    {/* Provider logo with status ring */}
                    <div className="relative">
                      <div className={`p-2 rounded-xl bg-studio-obsidian/50 ${isHealthy && isEnabled ? 'ring-2 ring-led-green shadow-lg shadow-led-green/30' : !isEnabled ? 'ring-2 ring-studio-slate' : 'ring-2 ring-led-red'}`}>
                        <ProviderLogo name={provider.name} size={24} />
                      </div>

                      {/* Status LED */}
                      <div className="absolute -top-1 -right-1 flex gap-1">
                        <div className={`w-3 h-3 rounded-full ${isHealthy && isEnabled ? 'bg-led-green animate-led-pulse' : !isEnabled ? 'bg-studio-slate' : 'bg-led-red animate-led-pulse'}`} />
                      </div>
                    </div>

                    {/* Provider info */}
                    <div className="text-center min-w-0">
                      <div className="text-xs font-medium text-white truncate max-w-full">
                        {provider.display_name}
                      </div>
                      <Badge
                        status={isHealthy && isEnabled ? "healthy" : !isEnabled ? "pending" : "unhealthy"}
                        className="mt-1 text-xs"
                      />
                    </div>

                    {/* Mini VU meter for each provider */}
                    <VUMeter
                      level={isHealthy && isEnabled ? 75 : 0}
                      barCount={3}
                      height={12}
                      animated={isHealthy && isEnabled}
                    />
                  </div>
                );
              })}
            </div>
          </Card>
        </CollapsiblePanel>

        {/* Active Training Jobs */}
        {activeJobs.length > 0 && (
          <CollapsiblePanel
            title="Training Console"
            icon={<TrendingUp className="h-5 w-5 text-electric-400" />}
            defaultOpen={true}
          >
            <div className="space-y-4">
              {activeJobs.map((job) => (
                <Card key={job.id} variant="console" className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="flex flex-col items-center gap-1">
                        <div className="w-3 h-3 bg-electric-500 rounded-full animate-led-pulse" />
                        <span className="text-xs font-mono text-studio-silver">
                          CH{job.id.slice(-2)}
                        </span>
                      </div>

                      <div>
                        <p className="font-medium text-white">
                          Profile: {job.profile_id.slice(0, 8)}...
                        </p>
                        <p className="text-sm text-studio-silver">
                          Provider: {job.provider_name}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-6">
                      {/* Progress visualization */}
                      <div className="flex items-center gap-3">
                        <div className="w-32 h-3 rounded-full bg-studio-obsidian/50 overflow-hidden border border-studio-slate/30">
                          <div
                            className="h-full bg-gradient-to-r from-electric-500 to-electric-400 transition-all duration-500"
                            style={{ width: `${job.progress * 100}%` }}
                          />
                        </div>
                        <span className="text-sm font-mono text-studio-silver">
                          {(job.progress * 100).toFixed(0)}%
                        </span>
                      </div>

                      {/* Status badge */}
                      <Badge status={job.status} />

                      {/* Activity VU meter */}
                      <VUMeter level={job.progress * 100} barCount={5} height={16} />
                    </div>
                  </div>
                </Card>
              ))}
            </div>
          </CollapsiblePanel>
        )}

        {/* Recent Synthesis History */}
        {history.length > 0 && (
          <CollapsiblePanel
            title="Recent Activity Log"
            icon={<Clock className="h-5 w-5 text-secondary-400" />}
            actions={
              <Link
                to="/synthesis"
                className="text-sm text-primary-400 hover:text-primary-300 font-medium transition-colors"
              >
                View All →
              </Link>
            }
            defaultOpen={false}
          >
            <Card variant="console" className="overflow-hidden">
              <div className="space-y-3">
                {history.slice(0, 5).map((item: any, index) => (
                  <div
                    key={item.id}
                    className="flex items-center gap-4 p-3 rounded-lg bg-studio-charcoal/30 hover:bg-studio-charcoal/50 transition-all duration-300"
                  >
                    <div className="flex flex-col items-center gap-1">
                      <div className="w-2 h-2 bg-led-green rounded-full" />
                      <span className="text-xs font-mono text-studio-silver">
                        {(index + 1).toString().padStart(2, '0')}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white truncate font-medium">
                        {item.text}
                      </p>
                      <div className="flex items-center gap-3 mt-1">
                        <span className="text-xs text-studio-silver">
                          {item.provider_name}
                        </span>
                        <span className="text-xs text-secondary-400">
                          {item.latency_ms}ms
                        </span>
                        <span className="text-xs text-studio-silver">
                          {new Date(item.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                    </div>

                    <WaveformVisualizer
                      height={16}
                      barCount={8}
                      animated={false}
                      color="secondary"
                      className="w-16"
                    />
                  </div>
                ))}
              </div>
            </Card>
          </CollapsiblePanel>
        )}
      </div>
    </div>
  );
}

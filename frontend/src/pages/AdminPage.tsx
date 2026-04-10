import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Shield,
  Save,
  RefreshCw,
  Download,
  Upload,
  Eye,
  EyeOff,
  Server,
  Database,
  Cpu,
  Activity,
  Lock,
  FolderOpen,
  Settings2,
  Bell,
  Heart,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";
import { Button } from "../components/ui/Button";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { useSystemSettingsStore } from "../stores/systemSettingsStore";
import { createLogger } from "../utils/logger";
import type { SystemSetting } from "../types";

const logger = createLogger("AdminPage");

const CATEGORY_META: Record<
  string,
  { label: string; icon: typeof Shield; description: string }
> = {
  general: {
    label: "General",
    icon: Settings2,
    description: "Application name, logging, debug mode",
  },
  auth: {
    label: "Authentication",
    icon: Lock,
    description: "JWT settings, auth mode, encryption keys",
  },
  storage: {
    label: "Storage",
    icon: FolderOpen,
    description: "File paths, upload limits, retention",
  },
  providers: {
    label: "Providers",
    icon: Cpu,
    description: "API keys, GPU service, default provider",
  },
  healing: {
    label: "Self-Healing",
    icon: Heart,
    description: "Thresholds, intervals, MCP bridge config",
  },
  notifications: {
    label: "Notifications",
    icon: Bell,
    description: "Webhooks and email alerts",
  },
};

const SECRET_MASK = "••••••••";

export default function AdminPage() {
  const {
    settings,
    systemInfo,
    loading,
    saving,
    fetchSettings,
    fetchSystemInfo,
    bulkUpdateSettings,
    backupSettings,
    restoreSettings,
    seedDefaults,
  } = useSystemSettingsStore();

  const [dirtyValues, setDirtyValues] = useState<Record<string, string>>({});
  const [visibleSecrets, setVisibleSecrets] = useState<Set<string>>(new Set());
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    fetchSettings(undefined, true);
    fetchSystemInfo();
  }, [fetchSettings, fetchSystemInfo]);

  // Group settings by category
  const grouped = useMemo(() => {
    const map: Record<string, SystemSetting[]> = {};
    for (const s of settings) {
      if (!map[s.category]) map[s.category] = [];
      map[s.category].push(s);
    }
    return map;
  }, [settings]);

  const categories = useMemo(
    () => Object.keys(CATEGORY_META).filter((c) => grouped[c]?.length),
    [grouped]
  );

  const handleRefresh = useCallback(async () => {
    setRefreshing(true);
    await fetchSettings(undefined, true);
    await fetchSystemInfo();
    setRefreshing(false);
    setDirtyValues({});
    toast.success("Settings refreshed");
  }, [fetchSettings, fetchSystemInfo]);

  const handleValueChange = (category: string, key: string, value: string) => {
    setDirtyValues((prev) => ({ ...prev, [`${category}.${key}`]: value }));
  };

  const getDirtyCount = (category: string) => {
    return Object.keys(dirtyValues).filter((k) => k.startsWith(`${category}.`))
      .length;
  };

  const handleSaveCategory = async (category: string) => {
    const updates = Object.entries(dirtyValues)
      .filter(([k]) => k.startsWith(`${category}.`))
      .map(([k, v]) => ({ key: k.split(".").slice(1).join("."), value: v }));

    if (updates.length === 0) return;

    try {
      await bulkUpdateSettings(category, updates);
      // Clear dirty values for this category
      setDirtyValues((prev) => {
        const next = { ...prev };
        for (const key of Object.keys(next)) {
          if (key.startsWith(`${category}.`)) delete next[key];
        }
        return next;
      });
      toast.success(`${CATEGORY_META[category]?.label || category} settings saved`);
    } catch {
      toast.error("Failed to save settings");
    }
  };

  const toggleSecretVisibility = (fullKey: string) => {
    setVisibleSecrets((prev) => {
      const next = new Set(prev);
      if (next.has(fullKey)) {
        next.delete(fullKey);
      } else {
        next.add(fullKey);
      }
      return next;
    });
  };

  const handleBackup = async () => {
    try {
      const backup = await backupSettings();
      const blob = new Blob([JSON.stringify(backup)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `atlas-vox-settings-backup-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Backup created (${backup.settings_count} settings)`);
      logger.info("backup_created", { count: backup.settings_count });
    } catch {
      toast.error("Backup failed");
    }
  };

  const handleRestore = async () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const text = await file.text();
        const backup = JSON.parse(text);
        const count = await restoreSettings(backup.data);
        toast.success(`Restored ${count} settings`);
        logger.info("settings_restored", { count });
      } catch {
        toast.error("Restore failed — invalid backup file");
      }
    };
    input.click();
  };

  const handleSeed = async () => {
    try {
      const count = await seedDefaults();
      if (count > 0) {
        toast.success(`Seeded ${count} new default settings`);
      } else {
        toast.info("All defaults already exist");
      }
    } catch {
      toast.error("Seed failed");
    }
  };

  if (loading && settings.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <Shield className="h-7 w-7 text-primary-500" />
          <div>
            <h1 className="text-2xl font-bold">Administration</h1>
            <p className="text-sm text-[var(--color-text-secondary)]">
              System settings, secrets, and diagnostics
            </p>
          </div>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="secondary" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button variant="secondary" onClick={handleBackup}>
            <Download className="h-4 w-4" /> Backup
          </Button>
          <Button variant="secondary" onClick={handleRestore}>
            <Upload className="h-4 w-4" /> Restore
          </Button>
          <Button variant="ghost" onClick={handleSeed}>
            <RefreshCw className="h-4 w-4" /> Seed Defaults
          </Button>
        </div>
      </div>

      {/* System Info */}
      {systemInfo && (
        <CollapsiblePanel
          title="System Info"
          icon={<Server className="h-4 w-4 text-blue-500" />}
          id="admin-system-info"
          defaultOpen
        >
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            <InfoCard label="Version" value={systemInfo.version} />
            <InfoCard label="Environment" value={systemInfo.app_env} />
            <InfoCard
              label="Database"
              value={systemInfo.database_type}
              icon={<Database className="h-4 w-4" />}
            />
            <InfoCard
              label="Providers"
              value={`${systemInfo.active_providers}/${systemInfo.provider_count}`}
              icon={<Cpu className="h-4 w-4" />}
            />
            <InfoCard
              label="Redis"
              value={systemInfo.redis_connected ? "Connected" : "Offline"}
              color={systemInfo.redis_connected ? "text-green-500" : "text-red-500"}
            />
            <InfoCard
              label="Celery"
              value={systemInfo.celery_connected ? "Connected" : "Offline"}
              color={systemInfo.celery_connected ? "text-green-500" : "text-red-500"}
            />
          </div>
          <div className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-4">
            <InfoCard label="Profiles" value={String(systemInfo.profile_count)} />
            <InfoCard
              label="Syntheses"
              value={String(systemInfo.total_synthesis)}
            />
            <InfoCard
              label="Healing"
              value={systemInfo.healing_running ? "Running" : "Stopped"}
              color={
                systemInfo.healing_running ? "text-green-500" : "text-yellow-500"
              }
              icon={<Activity className="h-4 w-4" />}
            />
            <InfoCard
              label="Uptime"
              value={formatUptime(systemInfo.uptime_seconds)}
            />
          </div>
        </CollapsiblePanel>
      )}

      {/* Settings by Category */}
      {categories.map((category) => {
        const meta = CATEGORY_META[category];
        const items = grouped[category] || [];
        const dirtyCount = getDirtyCount(category);
        const Icon = meta?.icon || Settings2;

        return (
          <CollapsiblePanel
            key={category}
            title={meta?.label || category}
            icon={<Icon className="h-4 w-4 text-primary-500" />}
            id={`admin-${category}`}
            badge={
              dirtyCount > 0 ? (
                <span className="rounded-full bg-orange-500 px-2 py-0.5 text-xs text-white">
                  {dirtyCount} modified
                </span>
              ) : undefined
            }
            actions={
              <Button
                variant="primary"
                size="sm"
                disabled={dirtyCount === 0 || saving}
                onClick={() => handleSaveCategory(category)}
              >
                {saving ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Save className="h-3 w-3" />
                )}
                Save
              </Button>
            }
          >
            {meta?.description && (
              <p className="mb-4 text-sm text-[var(--color-text-secondary)]">
                {meta.description}
              </p>
            )}
            <div className="space-y-3">
              {items.map((setting) => {
                const fullKey = `${setting.category}.${setting.key}`;
                const isDirty = fullKey in dirtyValues;
                const isSecretVisible = visibleSecrets.has(fullKey);
                const displayValue = isDirty
                  ? dirtyValues[fullKey]
                  : setting.is_secret && !isSecretVisible
                    ? SECRET_MASK
                    : setting.value;

                return (
                  <div
                    key={fullKey}
                    className={`flex flex-col gap-1.5 rounded-[var(--radius)] border p-3 ${
                      isDirty
                        ? "border-orange-500/50 bg-orange-500/5"
                        : "border-[var(--color-border)]"
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <label className="text-sm font-medium font-mono">
                          {setting.key}
                        </label>
                        {setting.is_secret && (
                          <Lock className="h-3 w-3 text-yellow-500" />
                        )}
                        <span className="text-[10px] text-[var(--color-text-secondary)] bg-[var(--color-bg-secondary)] px-1.5 py-0.5 rounded">
                          {setting.value_type}
                        </span>
                        {isDirty && (
                          <span className="text-[10px] text-orange-500 font-medium">
                            (modified)
                          </span>
                        )}
                      </div>
                      {setting.is_secret && (
                        <button
                          type="button"
                          onClick={() => toggleSecretVisibility(fullKey)}
                          className="text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
                          aria-label={isSecretVisible ? "Hide secret" : "Show secret"}
                        >
                          {isSecretVisible ? (
                            <EyeOff className="h-4 w-4" />
                          ) : (
                            <Eye className="h-4 w-4" />
                          )}
                        </button>
                      )}
                    </div>
                    {setting.description && (
                      <p className="text-xs text-[var(--color-text-secondary)]">
                        {setting.description}
                      </p>
                    )}
                    {setting.value_type === "bool" ? (
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() =>
                            handleValueChange(
                              setting.category,
                              setting.key,
                              isDirty
                                ? dirtyValues[fullKey] === "true"
                                  ? "false"
                                  : "true"
                                : setting.value === "true"
                                  ? "false"
                                  : "true"
                            )
                          }
                          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                            (isDirty ? dirtyValues[fullKey] : setting.value) ===
                            "true"
                              ? "bg-primary-500"
                              : "bg-gray-400 dark:bg-gray-600"
                          }`}
                          role="switch"
                          aria-checked={
                            (isDirty ? dirtyValues[fullKey] : setting.value) ===
                            "true"
                          }
                        >
                          <span
                            className={`inline-block h-4 w-4 rounded-full bg-white shadow transition-transform ${
                              (isDirty
                                ? dirtyValues[fullKey]
                                : setting.value) === "true"
                                ? "translate-x-6"
                                : "translate-x-1"
                            }`}
                          />
                        </button>
                        <span className="text-sm">
                          {(isDirty ? dirtyValues[fullKey] : setting.value) ===
                          "true"
                            ? "Enabled"
                            : "Disabled"}
                        </span>
                      </div>
                    ) : (
                      <input
                        type={
                          setting.is_secret && !isSecretVisible
                            ? "password"
                            : "text"
                        }
                        value={displayValue}
                        onChange={(e) =>
                          handleValueChange(
                            setting.category,
                            setting.key,
                            e.target.value
                          )
                        }
                        placeholder={setting.is_secret ? "Enter value..." : ""}
                        className="w-full rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-1.5 text-sm font-mono focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                      />
                    )}
                  </div>
                );
              })}
            </div>
          </CollapsiblePanel>
        );
      })}
    </div>
  );
}

function InfoCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon?: React.ReactNode;
  color?: string;
}) {
  return (
    <div className="rounded-[var(--radius)] border border-[var(--color-border)] bg-[var(--color-bg)] p-3 text-center card-styled">
      {icon && (
        <div className={`mx-auto mb-1 ${color || "text-[var(--color-text-secondary)]"}`}>
          {icon}
        </div>
      )}
      <p className={`text-lg font-bold ${color || ""}`}>{value}</p>
      <p className="text-xs text-[var(--color-text-secondary)]">{label}</p>
    </div>
  );
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 24) {
    const d = Math.floor(h / 24);
    return `${d}d ${h % 24}h`;
  }
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

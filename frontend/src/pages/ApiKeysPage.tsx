import { useEffect, useState } from "react";
import { Copy, Trash2, Plus, Key } from "lucide-react";
import { toast } from "sonner";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { EmptyState } from "../components/ui/EmptyState";
import { ConfirmDialog } from "../components/ui/ConfirmDialog";
import { api } from "../services/api";
import type { ApiKeyResponse } from "../types";
import { createLogger } from "../utils/logger";

const logger = createLogger("ApiKeysPage");

const ALL_SCOPES = ["read", "write", "synthesize", "train", "admin"];

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKeyResponse[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Set<string>>(new Set(["read", "synthesize"]));
  const [newKey, setNewKey] = useState<string | null>(null);
  const [revokeTarget, setRevokeTarget] = useState<string | null>(null);

  const load = async () => { const { api_keys } = await api.listApiKeys(); setKeys(api_keys); };
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    logger.info("key_create", { name, scopes: Array.from(scopes) });
    try {
      const result = await api.createApiKey({ name, scopes: Array.from(scopes) });
      setNewKey(result.key);
      logger.info("key_created", { name });
      toast.success("API key created — copy it now");
      load();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to create key";
      logger.error("key_create_error", { error: message });
      toast.error(message);
    }
  };

  const handleRevoke = async (id: string) => {
    logger.info("key_revoke", { key_id: id });
    try {
      await api.revokeApiKey(id);
      logger.info("key_revoked", { key_id: id });
      toast.success("Key revoked");
      load();
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Failed to revoke key";
      logger.error("key_revoke_error", { key_id: id, error: message });
      toast.error(message);
    } finally {
      setRevokeTarget(null);
    }
  };

  const toggleScope = (s: string) => { const n = new Set(scopes); if (n.has(s)) n.delete(s); else n.add(s); setScopes(n); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">API Keys</h1>
        <Button onClick={() => { setShowCreate(true); setNewKey(null); setName(""); }}><Plus className="h-4 w-4" /> New Key</Button>
      </div>
      <CollapsiblePanel
        title={`API Keys (${keys.length})`}
        icon={<Key className="h-4 w-4 text-primary-500" />}
        badge={keys.length === 0 ? undefined : <span className="text-xs text-[var(--color-text-secondary)]">{keys.filter((k) => k.is_active !== false).length} active</span>}
      >
        {keys.length === 0 ? (
          <EmptyState
            icon={<Key className="h-12 w-12" />}
            title="No API keys"
            description="Create an API key to integrate Atlas Vox with your applications."
            action={{ label: "Create API Key", onClick: () => { setShowCreate(true); setNewKey(null); setName(""); } }}
          />
        ) : (
          <div className="overflow-x-auto -mx-4 px-4">
            <table className="w-full text-sm min-w-[500px]">
              <thead>
                <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                  <th className="pb-2 font-medium">Name</th>
                  <th className="pb-2 font-medium">Key</th>
                  <th className="pb-2 font-medium">Scopes</th>
                  <th className="pb-2 font-medium">Status</th>
                  <th className="pb-2 font-medium hidden sm:table-cell">Created</th>
                  <th className="pb-2" />
                </tr>
              </thead>
              <tbody>
                {keys.map((k) => (
                  <tr key={k.id} className="border-b border-[var(--color-border)] last:border-0">
                    <td className="py-2 font-medium">{k.name}</td>
                    <td className="py-2 font-mono text-xs">{k.key_prefix}...</td>
                    <td className="py-2 text-xs">{Array.isArray(k.scopes) ? k.scopes.join(", ") : k.scopes}</td>
                    <td className="py-2"><Badge status={k.is_active !== false ? "healthy" : "revoked"} /></td>
                    <td className="py-2 text-xs text-[var(--color-text-secondary)] hidden sm:table-cell">{new Date(k.created_at).toLocaleDateString()}</td>
                    <td className="py-2"><Button size="sm" variant="ghost" onClick={() => setRevokeTarget(k.id)}><Trash2 className="h-3 w-3" /></Button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CollapsiblePanel>
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={newKey ? "API Key Created" : "Create API Key"}>
        {newKey ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">Copy this key now. It will not be shown again.</p>
            <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <code className="flex-1 text-xs break-all">{newKey}</code>
              <Button size="sm" variant="ghost" onClick={() => { logger.info("key_copied"); navigator.clipboard.writeText(newKey); toast.success("Copied"); }}><Copy className="h-4 w-4" /></Button>
            </div>
            <Button className="w-full" onClick={() => setShowCreate(false)}>Done</Button>
          </div>
        ) : (
          <div className="space-y-4">
            <Input label="Key Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="My API Key" />
            <div>
              <label className="block text-sm font-medium mb-2">Scopes</label>
              <div className="flex flex-wrap gap-2">
                {ALL_SCOPES.map((s) => (
                  <button key={s} onClick={() => toggleScope(s)} className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${scopes.has(s) ? "border-primary-500 bg-primary-50 text-primary-700 dark:bg-primary-900 dark:text-primary-300" : "border-[var(--color-border)] text-[var(--color-text-secondary)]"}`}>{s}</button>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="secondary" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button onClick={handleCreate}>Create Key</Button>
            </div>
          </div>
        )}
      </Modal>
      <ConfirmDialog
        open={revokeTarget !== null}
        onClose={() => setRevokeTarget(null)}
        onConfirm={() => { if (revokeTarget) handleRevoke(revokeTarget); }}
        title="Revoke API Key"
        description="Are you sure you want to revoke this API key? Any applications using this key will lose access immediately."
        confirmLabel="Revoke Key"
        variant="danger"
      />
    </div>
  );
}

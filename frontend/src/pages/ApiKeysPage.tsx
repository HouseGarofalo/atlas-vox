import { useEffect, useState } from "react";
import { Copy, Trash2, Plus } from "lucide-react";
import { toast } from "sonner";
import { Card } from "../components/ui/Card";
import { Badge } from "../components/ui/Badge";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { api } from "../services/api";

const ALL_SCOPES = ["read", "write", "synthesize", "train", "admin"];

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<Set<string>>(new Set(["read", "synthesize"]));
  const [newKey, setNewKey] = useState<string | null>(null);

  const load = async () => { const { api_keys } = await api.listApiKeys(); setKeys(api_keys); };
  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!name.trim()) return;
    try {
      const result = await api.createApiKey({ name, scopes: Array.from(scopes) });
      setNewKey(result.key);
      toast.success("API key created — copy it now");
      load();
    } catch (e: any) { toast.error(e.message); }
  };

  const handleRevoke = async (id: string) => {
    if (!confirm("Revoke this API key?")) return;
    await api.revokeApiKey(id); toast.success("Key revoked"); load();
  };

  const toggleScope = (s: string) => { const n = new Set(scopes); if (n.has(s)) n.delete(s); else n.add(s); setScopes(n); };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">API Keys</h1>
        <Button onClick={() => { setShowCreate(true); setNewKey(null); setName(""); }}><Plus className="h-4 w-4" /> New Key</Button>
      </div>
      {keys.length === 0 ? (
        <Card className="py-12 text-center"><p className="text-[var(--color-text-secondary)]">No API keys yet.</p></Card>
      ) : (
        <Card>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--color-border)] text-left text-[var(--color-text-secondary)]">
                <th className="pb-2 font-medium">Name</th><th className="pb-2 font-medium">Key</th><th className="pb-2 font-medium">Scopes</th><th className="pb-2 font-medium">Status</th><th className="pb-2 font-medium">Created</th><th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id} className="border-b border-[var(--color-border)] last:border-0">
                  <td className="py-2 font-medium">{k.name}</td>
                  <td className="py-2 font-mono text-xs">{k.key_prefix}...</td>
                  <td className="py-2 text-xs">{k.scopes}</td>
                  <td className="py-2"><Badge status={k.active ? "healthy" : "error"} /></td>
                  <td className="py-2 text-xs text-[var(--color-text-secondary)]">{new Date(k.created_at).toLocaleDateString()}</td>
                  <td className="py-2"><Button size="sm" variant="ghost" onClick={() => handleRevoke(k.id)}><Trash2 className="h-3 w-3" /></Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
      <Modal open={showCreate} onClose={() => setShowCreate(false)} title={newKey ? "API Key Created" : "Create API Key"}>
        {newKey ? (
          <div className="space-y-4">
            <p className="text-sm text-[var(--color-text-secondary)]">Copy this key now. It will not be shown again.</p>
            <div className="flex items-center gap-2 rounded-lg border border-[var(--color-border)] bg-[var(--color-bg-secondary)] p-3">
              <code className="flex-1 text-xs break-all">{newKey}</code>
              <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(newKey); toast.success("Copied"); }}><Copy className="h-4 w-4" /></Button>
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
    </div>
  );
}

/**
 * Shared ConfigField component — renders a provider configuration field.
 * Extracted from ProviderConfigCard and ProvidersPage to eliminate duplication.
 *
 * Supports text, password (with toggle visibility), and select (with optgroups).
 */

import { Eye, EyeOff } from "lucide-react";
import type { ProviderFieldSchema } from "../../types";

export interface ConfigFieldProps {
  field: ProviderFieldSchema;
  value: string;
  isDirty?: boolean;
  isSecretVisible?: boolean;
  originalValue?: string;
  onChange: (value: string) => void;
  onToggleVisibility?: () => void;
}

const INPUT_CLASS =
  "h-10 w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 text-sm text-[var(--color-text)] focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500";

export function ConfigField({
  field,
  value,
  isDirty = false,
  isSecretVisible = false,
  originalValue = "",
  onChange,
  onToggleVisibility,
}: ConfigFieldProps) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-1 text-sm font-medium text-[var(--color-text)]">
        {field.label}
        {field.required && <span className="text-red-500">*</span>}
        {isDirty && <span className="ml-1 text-xs text-primary-500">(modified)</span>}
      </label>
      {field.field_type === "select" ? (
        <select
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className={INPUT_CLASS}
        >
          <option value="">{field.default ? `Default: ${field.default}` : "Select..."}</option>
          {renderSelectOptions(field.options ?? [])}
        </select>
      ) : field.field_type === "password" ? (
        <div className="relative">
          <input
            type={isSecretVisible ? "text" : "password"}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={originalValue || field.default || ""}
            className={INPUT_CLASS + " pr-10"}
          />
          {onToggleVisibility && (
            <button
              type="button"
              onClick={onToggleVisibility}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--color-text-secondary)] hover:text-[var(--color-text)]"
              aria-label={isSecretVisible ? "Hide value" : "Show value"}
            >
              {isSecretVisible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          )}
        </div>
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.default || ""}
          className={INPUT_CLASS}
        />
      )}
    </div>
  );
}

/** Parse select options with optional `---Group Name` optgroup separators. */
function renderSelectOptions(options: string[]) {
  const groups: { label: string | null; items: string[] }[] = [];
  let current: { label: string | null; items: string[] } = { label: null, items: [] };

  for (const opt of options) {
    if (opt.startsWith("---")) {
      if (current.items.length > 0 || current.label) groups.push(current);
      current = { label: opt.slice(3), items: [] };
    } else {
      current.items.push(opt);
    }
  }
  if (current.items.length > 0 || current.label) groups.push(current);

  return groups.map((g) =>
    g.label ? (
      <optgroup key={g.label} label={g.label}>
        {g.items.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </optgroup>
    ) : (
      g.items.map((opt) => (
        <option key={opt} value={opt}>{opt}</option>
      ))
    )
  );
}

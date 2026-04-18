/**
 * ProviderGrid — responsive card grid with an inline full-width edit panel.
 *
 * Extracted from ProvidersPage.tsx as part of P2-20 (decompose large pages).
 * Behaviour preserved: cards render in a 3-col grid and when one card is being
 * edited the edit panel appears directly after it and spans every column.
 */

import React from "react";
import { ProviderCard } from "./ProviderCard";
import { ProviderEditPanel } from "./ProviderEditPanel";
import type { Provider } from "../../types";

export interface ProviderGridProps {
  providers: Provider[];
  editingProvider: string | null;
  onToggleEdit: (name: string) => void;
  onCheckHealth: (name: string) => Promise<void>;
}

export function ProviderGrid({
  providers,
  editingProvider,
  onToggleEdit,
  onCheckHealth,
}: ProviderGridProps) {
  // Flat list so the edit panel can span full width at all breakpoints.
  const items: React.ReactNode[] = [];

  for (const provider of providers) {
    items.push(
      <ProviderCard
        key={provider.name}
        provider={provider}
        isEditing={editingProvider === provider.name}
        onToggleEdit={() => onToggleEdit(provider.name)}
        onCheckHealth={() => onCheckHealth(provider.name)}
      />,
    );

    if (editingProvider === provider.name) {
      items.push(
        <div
          key={`${provider.name}-edit`}
          className="col-span-1 sm:col-span-2 lg:col-span-3"
        >
          <ProviderEditPanel
            provider={provider}
            onClose={() => onToggleEdit(provider.name)}
          />
        </div>,
      );
    }
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {items}
    </div>
  );
}

/**
 * FilterPanel — search + provider/language/gender filters + library stats.
 *
 * Extracted from VoiceLibraryPage.tsx as part of P2-20 (decompose large pages).
 */

import { Search } from "lucide-react";
import { Card } from "../../components/ui/Card";
import { Select } from "../../components/ui/Select";
import WaveformVisualizer from "../../components/audio/WaveformVisualizer";

export interface FilterOption {
  value: string;
  label: string;
}

export interface FilterPanelProps {
  searchInput: string;
  onSearchChange: (value: string) => void;
  providerValue: string;
  onProviderChange: (value: string | null) => void;
  languageValue: string;
  onLanguageChange: (value: string | null) => void;
  genderValue: string;
  onGenderChange: (value: string | null) => void;
  providerOptions: FilterOption[];
  languageOptions: FilterOption[];
  genderOptions: FilterOption[];
  totalVoices: number;
  filteredCount: number;
}

export function FilterPanel({
  searchInput,
  onSearchChange,
  providerValue,
  onProviderChange,
  languageValue,
  onLanguageChange,
  genderValue,
  onGenderChange,
  providerOptions,
  languageOptions,
  genderOptions,
  totalVoices,
  filteredCount,
}: FilterPanelProps) {
  return (
    <Card variant="console" className="p-6">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Search Channel */}
        <div className="lg:col-span-2">
          <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
            Search Channel
          </label>
          <div className="relative">
            <Search className="absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-studio-silver" />
            <input
              type="text"
              placeholder="Search voices by name, ID, or provider..."
              value={searchInput}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full h-12 pl-12 pr-4 rounded-xl bg-studio-obsidian/50 border border-studio-slate/30 text-white placeholder:text-studio-silver/50 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-500/20 font-mono"
            />
            {/* Search activity indicator */}
            <div className="absolute right-4 top-1/2 -translate-y-1/2">
              <WaveformVisualizer
                height={16}
                barCount={6}
                animated={searchInput.length > 0}
                color="primary"
                className="w-12"
              />
            </div>
          </div>
        </div>

        {/* Filter Controls */}
        <div>
          <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
            Provider
          </label>
          <Select
            value={providerValue}
            onChange={(e) => onProviderChange(e.target.value || null)}
            options={providerOptions}
            className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
          />
        </div>

        <div>
          <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
            Language
          </label>
          <Select
            value={languageValue}
            onChange={(e) => onLanguageChange(e.target.value || null)}
            options={languageOptions}
            className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
          />
        </div>
      </div>

      {/* Additional filter row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-6 mt-6">
        <div>
          <label className="block text-xs font-mono text-studio-silver mb-3 uppercase tracking-wider">
            Gender
          </label>
          <Select
            value={genderValue}
            onChange={(e) => onGenderChange(e.target.value || null)}
            options={genderOptions}
            className="bg-studio-obsidian/50 border-studio-slate/30 text-white"
          />
        </div>

        {/* Library Stats */}
        <div className="lg:col-span-3 flex items-end gap-6">
          <div className="text-center">
            <div className="text-xs font-mono text-studio-silver mb-1">TOTAL VOICES</div>
            <div className="text-2xl font-bold text-white">{totalVoices}</div>
          </div>
          <div className="text-center">
            <div className="text-xs font-mono text-studio-silver mb-1">FILTERED</div>
            <div className="text-2xl font-bold text-secondary-400">{filteredCount}</div>
          </div>
          <div className="text-center">
            <div className="text-xs font-mono text-studio-silver mb-1">PROVIDERS</div>
            <div className="text-2xl font-bold text-electric-400">
              {providerOptions.length - 1}
            </div>
          </div>
        </div>
      </div>
    </Card>
  );
}

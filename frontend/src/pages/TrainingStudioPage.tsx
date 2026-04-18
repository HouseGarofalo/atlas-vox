/**
 * TrainingStudioPage — voice profile training orchestration.
 *
 * P2-20: decomposed from a 592-line mega-file. All presentation blocks live
 * in ./training/*; all side-effects + handlers live in useTrainingStudio.
 * This file is now pure layout/wiring.
 */

import { useSearchParams } from "react-router-dom";
import { CheckCircle, Cpu, History, Music, Sparkles } from "lucide-react";
import { Select } from "../components/ui/Select";
import { CollapsiblePanel } from "../components/ui/CollapsiblePanel";
import { ConnectionBanner } from "./training/ConnectionBanner";
import { AudioSamplesSection } from "./training/AudioSamplesSection";
import { AzureConsentBanner } from "./training/AzureConsentBanner";
import { TrainingReadinessPanel } from "./training/TrainingReadinessPanel";
import { TrainModelPanel } from "./training/TrainModelPanel";
import { TrainingHistoryList } from "./training/TrainingHistoryList";
import { SampleRecommendationsPanel } from "./training/SampleRecommendationsPanel";
import { useTrainingStudio } from "./training/useTrainingStudio";

export default function TrainingStudioPage() {
  const [searchParams] = useSearchParams();
  const studio = useTrainingStudio(searchParams.get("profile") || "");

  const profileOptions = studio.profiles.map((p) => ({
    value: p.id,
    label: `${p.name} (${p.provider_name})`,
  }));
  const profileJobs = studio.jobs.filter((j) => j.profile_id === studio.selectedProfile);
  const selectedProfileData = studio.profiles.find((p) => p.id === studio.selectedProfile);
  const isAzure = selectedProfileData?.provider_name === "azure_speech";
  const trainDisabled =
    studio.samples.length < (isAzure ? 2 : 1) ||
    (studio.readiness !== null && !studio.readiness.ready);

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Training Studio</h1>
      {studio.activeJobId && studio.connectionBanner && (
        <ConnectionBanner
          message={studio.connectionBanner}
          status={studio.connectionStatus}
        />
      )}
      <Select
        label="Voice Profile"
        value={studio.selectedProfile}
        onChange={(e) => studio.setSelectedProfile(e.target.value)}
        options={[{ value: "", label: "Select a profile..." }, ...profileOptions]}
      />

      {studio.selectedProfile && (
        <>
          <CollapsiblePanel
            title={`Audio Samples (${studio.samples.length})`}
            icon={<Music className="h-4 w-4 text-primary-500" />}
          >
            <AudioSamplesSection
              samples={studio.samples}
              sampleQualities={studio.sampleQualities}
              playingSampleId={studio.playingSampleId}
              enhancing={studio.enhancing}
              enhancingAll={studio.enhancingAll}
              checkingQuality={studio.checkingQuality}
              uploading={studio.uploading}
              preprocessing={studio.preprocessing}
              onUpload={studio.handleUpload}
              onRecord={studio.handleRecord}
              onPlaySample={studio.handlePlaySample}
              onPlaybackEnded={() => studio.setPlayingSampleId(null)}
              onEnhance={studio.handleEnhance}
              onCheckQuality={studio.handleCheckQuality}
              onEnhanceAll={studio.handleEnhanceAll}
              onPreprocess={studio.handlePreprocess}
            />
          </CollapsiblePanel>

          {isAzure && <AzureConsentBanner />}

          <CollapsiblePanel
            title="Record These Next"
            icon={<Sparkles className="h-4 w-4 text-electric-500" />}
            defaultOpen={studio.samples.length === 0}
          >
            <SampleRecommendationsPanel
              recommendations={studio.recommendations}
              method={studio.recommendationMethod}
              loading={studio.loadingRecommendations}
              onRefresh={studio.loadRecommendations}
              onCopy={studio.handleCopySentence}
            />
          </CollapsiblePanel>

          {studio.samples.length > 0 && (
            <CollapsiblePanel
              title="Training Readiness"
              icon={<CheckCircle className="h-4 w-4 text-green-500" />}
            >
              <TrainingReadinessPanel
                readiness={studio.readiness}
                loading={studio.loadingReadiness}
              />
            </CollapsiblePanel>
          )}

          <CollapsiblePanel
            title="Train Model"
            icon={<Cpu className="h-4 w-4 text-blue-500" />}
          >
            <TrainModelPanel
              onStart={studio.handleStartTraining}
              disabled={trainDisabled}
              readiness={studio.readiness}
              progress={studio.progress}
            />
          </CollapsiblePanel>

          {profileJobs.length > 0 && (
            <CollapsiblePanel
              title="Training History"
              icon={<History className="h-4 w-4 text-gray-500" />}
              defaultOpen={false}
            >
              <TrainingHistoryList
                jobs={profileJobs}
                onCancel={studio.handleCancelJob}
              />
            </CollapsiblePanel>
          )}
        </>
      )}
    </div>
  );
}

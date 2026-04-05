# Atlas Vox Feature Implementation Roadmap

**Based on Competitive Analysis (April 2026)**  
**Target: Close top 5 feature gaps identified in market research**

---

## Overview

This roadmap prioritizes high-impact features that are:
1. **Feasible** to implement in 2-6 weeks
2. **Differentiating** vs. competitors
3. **Enterprise-focused** to justify self-hosted deployment

---

## Quick-Win Features (Ship This Month)

### 1. Usage Analytics Dashboard ⭐⭐⭐

**Problem:** Enterprise buyers can't see costs or usage by provider (major gap vs. ElevenLabs, Murf, Play.ht, Speechify)

**What to Build:**
- Dashboard showing:
  - Characters synthesized per provider (daily/monthly)
  - Estimated cost per provider
  - Provider uptime/latency metrics
  - Peak usage hours
- Metrics stored per synthesis request in database
- Prometheus exporter for self-hosted observability

**User Story:**
> "As an enterprise admin, I need to see monthly TTS costs by provider to optimize spending and understand which engines deliver best ROI."

**Effort:** 2-3 weeks
- Backend: Log synthesis metadata (provider, char count, latency) → PostgreSQL/SQLite
- Frontend: New Analytics page with date pickers, provider filters, cost charts
- Infra: Prometheus metrics, optional Grafana dashboard

**Why First:** 
- Unblocks enterprise sales conversations
- Single biggest gap vs. SaaS competitors
- Minimal new logic required
- High perceived value

**Dependencies:** None (use existing synthesis logs)

---

### 2. Audio Post-Processing (Noise Reduction) ⭐⭐⭐

**Problem:** Synthesis output can have slight artifacts; competitors offer audio enhancement as standard

**What to Build:**
- "Polish Audio" post-synthesis step using RoFormer DeepFilterNet
  - Removes background noise, slight artifacts
  - Optional (not forced on all output)
- Toggle in synthesis UI: "Apply noise reduction"
- Model inference runs on synthesis server (or separate worker)

**User Story:**
> "As a podcaster, I want to remove any background noise from the synthesis output to ensure broadcast-quality audio."

**Effort:** 2 weeks
- Backend: Integrate RoFormer DeepFilterNet model (HuggingFace)
- API: Add `apply_noise_reduction: bool` parameter to synthesis endpoint
- Frontend: Checkbox in synthesis form + progress indicator
- Testing: Verify audio quality doesn't degrade

**Why Now:**
- Improves perceived quality (bigger than reality, but matters)
- Simple integration (one model, post-synthesis)
- Differentiates from competitors who don't offer
- Model is lightweight (~100MB)

**Implementation Details:**
```python
# Backend workflow
1. Synthesize text → WAV with provider
2. If apply_noise_reduction:
   - Load RoFormer model
   - Process WAV through denoiser
   - Return cleaned WAV
3. Return to user
```

**Feasibility:** High (proven open-source model)

---

### 3. Pronunciation Rules Storage ⭐⭐

**Problem:** No way to save custom pronunciation rules (e.g., "SQL" → "ess-queue-el"); WellSaid Labs has this as strength

**What to Build:**
- Pronunciation Rules table in database:
  ```
  - project_id
  - pattern (regex or literal)
  - pronunciation (text to replace with)
  - enabled (bool)
  ```
- Pre-synthesis text preprocessing:
  1. Load rules for project
  2. Apply regex/literal replacements
  3. Pass processed text to provider
- UI: Simple "Rules" page with table (add/edit/delete)

**User Story:**
> "As a medical professional, I need to ensure 'MRI' is always synthesized as 'em-ar-eye' consistently across all voices."

**Effort:** 1-2 weeks
- Backend: Create Rule model, apply in text preprocessing
- Frontend: Basic CRUD form for rules (table + modal)
- Testing: Verify rules apply before synthesis

**Why Now:**
- Enterprise/vertical-specific need (medical, legal, finance)
- Minimal code required
- No provider API changes needed
- High ROI for niche markets

**Example Rules:**
```
Pattern: MRI      → Pronunciation: em-ar-eye
Pattern: SQL      → Pronunciation: ess-queue-el
Pattern: API      → Pronunciation: ay-pee-eye
Pattern: MVP      → Pronunciation: minimum viable product
Pattern: Y\.O\.L\.O → Pronunciation: you only live once
```

**Feasibility:** High (simple string replacement)

---

### 4. Batch Synthesis Queue ⭐⭐

**Problem:** Can't upload CSV and synthesize 100+ items overnight; Play.ht and AWS Polly offer this

**What to Build:**
- API endpoint: `POST /api/v1/synthesis/batch`
  - Accept: CSV file with `text` column (required), `voice_id` (optional), `provider` (optional)
  - Returns: Job ID, status endpoint
- Celery task: Process queue asynchronously
  - Synthesize each row
  - Store outputs in S3/disk
  - Update job status
- UI: "Batch Synthesis" page
  - Upload CSV
  - Show progress (queued, processing, completed)
  - Download all outputs as ZIP

**User Story:**
> "As an e-learning producer, I want to upload a CSV of 1000 scripts and have them all synthesized overnight without waiting."

**Effort:** 2-3 weeks
- Backend: New endpoint, Celery task, output storage
- Frontend: Upload form, progress tracking, download
- Testing: CSV validation, large file handling, error recovery

**Why Now:**
- Unblocks podcast/e-learning/audiobook workflows
- Differentiates from simple real-time TTS
- Celery already in stack
- Medium-high impact

**CSV Format:**
```
text,voice_id,provider,speaker_name
"Hello, welcome to lesson 1",ElevenLabs-Female-1,elevenlabs,Narrator
"This is important information",Coqui-Male-Deep,coqui,Expert
```

**Feasibility:** Medium (Celery + storage handling)

---

## Medium-Term Features (Next 4-6 Weeks)

### 5. Voice Design Page (Text → Voice) ⭐⭐

**Problem:** Emerging trend (Voxtral TTS, 2025); no competitors have this yet except research prototypes

**What to Build:**
- "Voice Design" page where users describe:
  - Gender (male, female, neutral)
  - Age range (young, middle-aged, elderly)
  - Tone/personality (warm, energetic, calm, professional)
  - Accent (American, British, Australian, etc.)
  - Language
- Backend:
  - Translate description → SSML prosody hints
  - Try multiple providers with hints
  - Return 3-5 candidate voices
- UI: Sliders/buttons for attributes → generate → preview → save as profile

**User Story:**
> "As a game developer, I want to describe the voice I need ('warm, energetic female with slight Southern accent') and have the system suggest voices that match."

**Effort:** 4-5 weeks
- Backend: Voice attribute → SSML mapping logic, provider selection
- Frontend: Voice design form, preview carousel, save profiles
- Testing: Quality of attribute matching

**Why Medium-Term:**
- Emerging feature (not yet commoditized)
- High differentiation
- Requires more complex logic
- Medium ROI (primarily creative/gaming use cases)

**Implementation Approach:**
```python
# Backend logic
1. Parse user description
2. Map attributes to provider-specific hints:
   - ElevenLabs: emotion tone
   - XTTS: speaker characteristics
   - Fish Speech: emotion parameters
3. Synthesize short test phrase with each provider
4. Return candidates ranked by match quality
5. Let user preview and select favorite
```

**Feasibility:** Medium (requires experimentation with provider APIs)

---

### 6. Real-Time Voice Conversion ⭐⭐

**Problem:** Only Resemble.ai and Voice.ai have this; emerging capability

**What to Build:**
- New "Voice Conversion" tab
  - Stream text synthesis
  - Apply voice conversion model in parallel
  - Return converted audio in real-time
- Pipeline: Synthesis → Voice Conversion → Output
- Model: RVC (Retrieval-based Voice Conversion) or similar

**User Story:**
> "As a content creator, I want to convert all my voice-overs to sound like a celebrity voice instantly for entertainment."

**Effort:** 4-6 weeks
- Backend: Voice conversion model integration (RVC, so-vits-svc)
- API: Streaming endpoint for real-time conversion
- Frontend: Voice selection + preview
- Testing: Audio quality, latency, synchronization

**Why Medium-Term:**
- Higher complexity (model inference + streaming)
- Emerging market (real-time voice changing)
- High novelty/fun factor
- Medium ROI (entertainment use case)

**Feasibility:** Medium-High (RVC models available, but requires optimization)

---

### 7. Multi-User Teams & Workspaces ⭐⭐

**Problem:** Enterprise deployments need isolation/RBAC; Murf.ai has full workspace features

**What to Build:**
- Organizations → Projects → Team Members structure:
  - Organization admin creates teams
  - Invite users with roles (Admin, Editor, Viewer)
  - Project-scoped permissions
  - Shared profiles/templates per team
- API key management per team/project
- Audit logging (who synthesized what, when)

**User Story:**
> "As a team lead, I need to manage synthesis permissions across my team, track who created which voice profiles, and isolate projects by client."

**Effort:** 5-6 weeks
- Backend: Organization/Project/Team/RBAC models
- Frontend: Team management UI, project switcher
- Auth: Multi-tenant architecture
- Testing: Permission enforcement, audit trails

**Why Medium-Term:**
- Largest code change (touches auth/data layer)
- Essential for multi-user deployments
- Medium ROI initially (not all deployments need this)
- High ROI long-term (unlocks enterprise sales)

**Feasibility:** Medium (auth/RBAC complexity, but well-trodden path)

---

## Future Features (Lower Priority)

### 8. Custom Voice Training UI

**Problem:** Can train voices via CLI (Coqui, GPT-SoVITS) but no user-friendly interface

**What to Build:**
- "Train Custom Voice" workflow:
  1. Upload 5-60s audio sample
  2. Select which providers support training (Coqui, Fish Speech)
  3. Click "Train" → async Celery job
  4. Show progress, quality metrics
  5. Deploy as new voice profile
- UI: Wizard-style form with progress tracking

**Effort:** 6-8 weeks
- Backend: Training job orchestration, progress tracking
- Frontend: Training wizard, quality assessment
- Testing: Training reliability, voice quality

**ROI:** High (voice customization), but niche audience (not all users train voices)

**Feasibility:** High (wrapper around existing provider training)

---

### 9. Imperceptible Audio Watermarking

**Problem:** Emerging compliance/authenticity need; Resemble.ai has PerTh watermarking

**What to Build:**
- Optional watermarking on synthesis output
- Embed imperceptible marker proving AI-generation
- Detectable by watermark decoder (for verification)
- Compliance/authenticity use case (prove AI origin)

**Effort:** 3-4 weeks
- Backend: Watermarking model integration (PerTh or similar)
- API: Optional parameter on synthesis
- Testing: Watermark robustness (survives compression, etc.)

**ROI:** Low-Medium (compliance edge case, but emerging)

**Feasibility:** Medium (requires watermarking algorithm)

---

### 10. AI Dubbing + Video Sync

**Problem:** Speechify, ElevenLabs have this; high demand for localization

**What to Build:**
- Video timeline editor
- Sync speech synthesis to video scenes
- Preserve pauses, timing
- Multi-language dubbing workflow

**Effort:** 8-10 weeks
- Backend: Video analysis, speech timing alignment
- Frontend: Timeline editor (complex UI)
- Testing: Sync accuracy, performance

**ROI:** Very High (localization workflow), but high effort

**Feasibility:** Medium-High (complex, but achievable with libraries like ffmpeg-python)

---

## Implementation Prioritization Matrix

| Feature | Effort | ROI | Enterprise? | Timeline |
|---------|--------|-----|-----------|----------|
| **Analytics Dashboard** | 2-3w | ⭐⭐⭐ | ✅ | **Week 1** |
| **Noise Reduction** | 2w | ⭐⭐⭐ | ⚠️ | **Week 2** |
| **Pronunciation Rules** | 1-2w | ⭐⭐ | ✅ | **Week 3** |
| **Batch Queue** | 2-3w | ⭐⭐ | ✅ | **Week 4-5** |
| **Voice Design** | 4-5w | ⭐⭐ | ⚠️ | **Month 2** |
| **Real-Time Conversion** | 4-6w | ⭐⭐ | ⚠️ | **Month 2** |
| **Multi-User Teams** | 5-6w | ⭐⭐⭐ | ✅ | **Month 2-3** |
| **Custom Training UI** | 6-8w | ⭐⭐⭐ | ⚠️ | **Month 3** |
| **Watermarking** | 3-4w | ⭐ | ✅ | **Backlog** |
| **AI Dubbing + Video** | 8-10w | ⭐⭐⭐ | ✅ | **Backlog** |

---

## Recommended 12-Week Roadmap

### **Month 1: Enterprise Basics (Foundation)**

**Week 1:** Analytics Dashboard (cost visibility)
- Cost by provider, usage trends, uptime metrics
- Unblocks enterprise sales conversations

**Week 2:** Noise Reduction (audio quality)
- Post-synthesis denoising
- Improves perceived quality

**Week 3-4:** Pronunciation Rules + Batch Queue
- Custom lexicons for enterprise terminology
- CSV batch processing for bulk workflows

**Outcome:** Atlas now offers **4 features competitors lack** while maintaining developer-friendly aggregation

---

### **Month 2: Creativity + Scale (Differentiation)**

**Week 5-6:** Voice Design Page (emergen 2025 trend)
- Text descriptions → voice profiles
- Differentiating feature

**Week 7-8:** Real-Time Voice Conversion (experimental)
- Voice conversion pipeline
- Novel capability

---

### **Month 3: Enterprise Scale (Multi-Tenant)**

**Week 9-12:** Multi-User Teams & Workspaces
- Organizations, projects, RBAC
- Audit logging
- Unlocks enterprise deployments

---

## Success Metrics

After implementing Tier 1 (Weeks 1-4):

- ✅ **Enterprise RFP Response Rate:** "Do you have cost analytics?" → Yes
- ✅ **Creator Workflow Time:** "How long to process 100 texts?" → <1 minute setup
- ✅ **Quality Perception:** A/B test noise-reduced vs. raw output → Preference shift
- ✅ **Unique Features Count:** Features no competitor has → +4 (analytics, noise, rules, batch)

---

## Competitive Positioning After Roadmap

**Current Atlas Vox Message:**
> "Multi-provider TTS aggregation with voice comparison"

**After 12-Week Roadmap:**
> "The Self-Hosted, Cost-Transparent, Multi-Provider TTS Hub for Enterprise and Creators"

**Key Differentiators:**
1. ✅ **Multi-provider** (9 providers in one interface)
2. ✅ **Cost visibility** (see spending by engine)
3. ✅ **Quality assurance** (noise reduction, audio polish)
4. ✅ **Scale** (batch processing for bulk workflows)
5. ✅ **Enterprise ready** (RBAC, audit logging)
6. ✅ **Emerging features** (voice design, real-time conversion)

---

## Resource Estimates

**Team Size:** 1 full-stack engineer

| Phase | Weeks | Focus |
|-------|-------|-------|
| Month 1 | 4 | Analytics, audio post-processing, batch processing |
| Month 2 | 4 | Voice design, real-time features |
| Month 3 | 4 | Enterprise features (RBAC, multi-tenant) |

**Total:** 12 weeks = **3-month sprint** to close all top gaps

---

## References & Sources

- [Commercial Platform Analysis](./competitive_analysis.md)
- [Feature Gap Matrix](./feature_gap_comparison.md)
- [OpenVoice GitHub](https://github.com/myshell-ai/OpenVoice)
- [RVC Voice Conversion](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
- [RoFormer DeepFilterNet](https://huggingface.co/diodiogod/RoFormer-Dereverb)
- [Coqui TTS](https://github.com/coqui-ai/TTS)

---

**Document Version:** 1.0  
**Created:** April 5, 2026  
**Next Review:** Before sprint planning

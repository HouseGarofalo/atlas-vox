# Atlas Vox CLI Reference

> **Command-line interface for voice profile management, training, synthesis, and system administration.**

Atlas Vox ships a full-featured CLI built on [Typer](https://typer.tiangolo.com/) with [Rich](https://github.com/Textualize/rich) terminal output. Every operation available through the web UI and REST API is also accessible from the terminal.

---

## Table of Contents

- [Installation](#installation)
- [Global Commands](#global-commands)
  - [version](#version)
  - [serve](#serve)
  - [init](#init)
- [profiles -- Voice Profile Management](#profiles----voice-profile-management)
  - [profiles list](#profiles-list)
  - [profiles create](#profiles-create)
  - [profiles delete](#profiles-delete)
- [train -- Training Operations](#train----training-operations)
  - [train upload](#train-upload)
  - [train start](#train-start)
  - [train status](#train-status)
- [synthesize -- Text-to-Speech](#synthesize----text-to-speech)
- [compare -- Voice Comparison](#compare----voice-comparison)
- [providers -- TTS Provider Management](#providers----tts-provider-management)
  - [providers list](#providers-list)
  - [providers health](#providers-health)
- [presets -- Persona Presets](#presets----persona-presets)
  - [presets list](#presets-list)
  - [presets create](#presets-create)
- [Shell Completions](#shell-completions)
- [Exit Codes](#exit-codes)

---

## Installation

Install Atlas Vox in editable (development) mode from the repository root:

```bash
cd backend
pip install -e ".[dev]"
```

This registers the `atlas-vox` entry point defined in `pyproject.toml`. Verify the installation:

```bash
atlas-vox version
```

**Prerequisites:**

| Dependency | Required | Purpose |
|---|---|---|
| Python 3.11+ | Yes | Runtime |
| espeak-ng | Recommended | Phonemizer for Kokoro, StyleTTS2, Piper |
| FFmpeg | Recommended | Audio format conversion |
| Redis | For training | Celery broker/backend |

---

## Global Commands

### `version`

Display the installed Atlas Vox version.

```bash
atlas-vox version
```

**Output:**

```
Atlas Vox v0.1.0
```

---

### `serve`

Start the Atlas Vox API server (FastAPI + Uvicorn).

```bash
atlas-vox serve [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--host` | `str` | `0.0.0.0` | Host to bind to |
| `--port` | `int` | `8100` | Port to listen on |
| `--mcp / --no-mcp` | `bool` | `false` | Enable MCP server endpoint |

**Examples:**

```bash
# Start with defaults (port 8100, all interfaces)
atlas-vox serve

# Start on a custom port with MCP enabled
atlas-vox serve --port 9000 --mcp

# Bind to localhost only
atlas-vox serve --host 127.0.0.1 --port 8080
```

**Output:**

```
Starting Atlas Vox server on 0.0.0.0:8100
MCP server enabled
INFO:     Uvicorn running on http://0.0.0.0:8100 (Press CTRL+C to quit)
```

> **Note:** The server runs with `--reload` enabled by default. For production, use `make docker-up` or configure Uvicorn directly.

---

### `init`

Initialize Atlas Vox: check system dependencies, create storage directories, and set up the database.

```bash
atlas-vox init
```

**No options.** This command is idempotent and safe to run multiple times.

**What it does:**

1. Checks for system dependencies (Python, espeak-ng, FFmpeg, Redis)
2. Creates the `storage/` directory tree:
   ```
   storage/
   +-- samples/
   +-- preprocessed/
   +-- output/
   +-- models/
       +-- piper/
       +-- coqui_xtts/
   ```
3. Initializes the SQLite database (creates tables)

**Output:**

```
Atlas Vox Initialization

       System Dependencies
+---------------+-----------+------------------------------------+
| Dependency    | Status    | Notes                              |
+---------------+-----------+------------------------------------+
| Python 3.11+  | OK Found  |                                    |
| espeak-ng     | OK Found  | Required by Kokoro, StyleTTS2,     |
|               |           | Piper                              |
| FFmpeg        | OK Found  | Audio format conversion            |
| Redis         | X Missing | Celery broker/backend              |
+---------------+-----------+------------------------------------+

OK Storage directories created
OK Database initialized

Some dependencies are missing. Install them for full functionality.
```

---

## profiles -- Voice Profile Management

Manage voice profiles: list, create, and delete.

```bash
atlas-vox profiles [COMMAND]
```

### `profiles list`

Display all voice profiles in a formatted table.

```bash
atlas-vox profiles list
```

**Output:**

```
                    Voice Profiles
+----------+----------------+----------+---------+---------+----------+
| ID       | Name           | Provider | Status  | Samples | Versions |
+----------+----------------+----------+---------+---------+----------+
| a1b2c3d4e5f6 | Narrator   | kokoro   | ready   |       8 |        2 |
| 7g8h9i0j1k2l | Assistant  | coqui_xt | training|       5 |        1 |
| m3n4o5p6q7r8 | Podcast    | eleven.. | error   |       3 |        0 |
+----------+----------------+----------+---------+---------+----------+
```

Status values are color-coded: **green** for `ready`, **blue** for `training`, **red** for `error`.

---

### `profiles create`

Create a new voice profile.

```bash
atlas-vox profiles create [OPTIONS]
```

| Option | Type | Default | Required | Description |
|---|---|---|---|---|
| `--name` | `str` | -- | Yes (prompted) | Profile name |
| `--provider` | `str` | `kokoro` | No | TTS provider name |
| `--language` | `str` | `en` | No | Language code (ISO 639-1) |
| `--description` | `str` | `""` | No | Human-readable description |

**Examples:**

```bash
# Interactive (prompts for name)
atlas-vox profiles create

# Fully specified
atlas-vox profiles create --name "News Anchor" --provider elevenlabs --language en --description "Professional news reading voice"

# Minimal -- uses Kokoro provider and English language by default
atlas-vox profiles create --name "My Voice"
```

**Output:**

```
OK Profile created: News Anchor (ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890)
```

---

### `profiles delete`

Delete a voice profile and all associated data.

```bash
atlas-vox profiles delete PROFILE_ID
```

| Argument | Type | Description |
|---|---|---|
| `PROFILE_ID` | `str` | UUID of the profile to delete |

**Example:**

```bash
atlas-vox profiles delete a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Output (success):**

```
OK Profile deleted: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

**Output (not found):**

```
X Profile not found: a1b2c3d4-e5f6-7890-abcd-ef1234567890
```

---

## train -- Training Operations

Upload audio samples and manage voice training jobs.

```bash
atlas-vox train [COMMAND]
```

### `train upload`

Bulk-upload audio samples from a local directory.

```bash
atlas-vox train upload PROFILE_ID DIRECTORY
```

| Argument | Type | Description |
|---|---|---|
| `PROFILE_ID` | `str` | Profile to upload samples for |
| `DIRECTORY` | `str` | Path to directory containing audio files |

**Supported audio formats:** `.wav`, `.mp3`, `.flac`, `.ogg`, `.m4a`

The command copies files into the Atlas Vox storage directory (`storage/samples/<profile_id>/`) and registers each sample in the database.

**Example:**

```bash
atlas-vox train upload a1b2c3d4 ./my-recordings/
```

**Output:**

```
Uploading... [####################################] 100%
OK Uploaded 12 samples for profile a1b2c3d4
```

The progress bar uses Rich's animated `SpinnerColumn` and `BarColumn` to show real-time upload progress.

---

### `train start`

Start a voice training job. Queues a Celery task for asynchronous execution.

```bash
atlas-vox train start PROFILE_ID [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `PROFILE_ID` | `str` | -- | Profile to train |
| `--provider` | `str` | `None` | Override the profile's default provider |

**Example:**

```bash
atlas-vox train start a1b2c3d4 --provider coqui_xtts
```

**Output:**

```
OK Training started!
  Job ID: f9e8d7c6-b5a4-3210-fedc-ba9876543210
  Provider: coqui_xtts
  Celery Task: abc123def456

Monitor: atlas-vox train status f9e8d7c6-b5a4-3210-fedc-ba9876543210
```

> **Requires:** Redis running for Celery task queue.

---

### `train status`

Check the status and progress of a training job.

```bash
atlas-vox train status JOB_ID
```

| Argument | Type | Description |
|---|---|---|
| `JOB_ID` | `str` | Training job UUID |

**Example:**

```bash
atlas-vox train status f9e8d7c6-b5a4-3210-fedc-ba9876543210
```

**Output (in progress):**

```
Job: f9e8d7c6-b5a4-3210-fedc-ba9876543210
Status: training
Progress: 65%
```

**Output (completed):**

```
Job: f9e8d7c6-b5a4-3210-fedc-ba9876543210
Status: completed
Progress: 100%
Version: v2-a1b2c3d4
```

**Output (failed):**

```
Job: f9e8d7c6-b5a4-3210-fedc-ba9876543210
Status: failed
Progress: 42%
Error: CUDA out of memory. Tried to allocate 2.00 GiB
```

---

## synthesize -- Text-to-Speech

Synthesize text to an audio file.

```bash
atlas-vox synthesize TEXT [OPTIONS]
```

| Argument / Option | Type | Default | Description |
|---|---|---|---|
| `TEXT` | `str` | -- | Text to synthesize |
| `--voice`, `-v` | `str` | -- | Voice profile ID (**required**) |
| `--output`, `-o` | `str` | `output.wav` | Output file path |
| `--speed` | `float` | `1.0` | Speech speed (0.5 to 2.0) |
| `--play`, `-p` | `bool` | `false` | Play audio after synthesis |
| `--format`, `-f` | `str` | `wav` | Output format: `wav`, `mp3`, `ogg` |

**Examples:**

```bash
# Basic synthesis
atlas-vox synthesize "Hello, world!" -v a1b2c3d4

# Custom output path and format
atlas-vox synthesize "Breaking news today..." -v a1b2c3d4 -o news.mp3 -f mp3

# Slow speed with auto-play
atlas-vox synthesize "Take your time." -v a1b2c3d4 --speed 0.75 --play

# Fast narration
atlas-vox synthesize "The quick brown fox jumps over the lazy dog." -v a1b2c3d4 --speed 1.5
```

**Output:**

```
OK Synthesized to: news.mp3
  Provider: elevenlabs
  Latency: 342ms
  Duration: 2.4s
```

**Audio Playback:** When `--play` is used, Atlas Vox detects the platform and uses the appropriate system player:

| Platform | Player |
|---|---|
| Windows | `start` |
| macOS | `afplay` |
| Linux | `aplay` |

---

## compare -- Voice Comparison

Synthesize the same text across multiple voice profiles for side-by-side comparison.

```bash
atlas-vox compare TEXT [OPTIONS]
```

| Argument / Option | Type | Description |
|---|---|---|
| `TEXT` | `str` | Text to synthesize across all voices |
| `--voice`, `-v` | `str` (repeatable) | Profile IDs to compare (minimum 2) |

**Example:**

```bash
atlas-vox compare "Welcome to the show." -v a1b2c3d4 -v e5f6g7h8 -v i9j0k1l2
```

**Output:**

```
                     Voice Comparison
+-----------+------------+---------+----------+------------------+
| Profile   | Provider   | Latency | Duration | Audio File       |
+-----------+------------+---------+----------+------------------+
| Narrator  | kokoro     |   120ms |     1.8s | output/abc123.wav|
| Assistant | elevenlabs |   340ms |     1.9s | output/def456.wav|
| Podcast   | coqui_xtts |   890ms |     2.0s | output/ghi789.wav|
+-----------+------------+---------+----------+------------------+
```

> **Note:** At least 2 voice profiles are required. The command exits with an error if fewer are provided.

---

## providers -- TTS Provider Management

List and health-check TTS providers.

```bash
atlas-vox providers [COMMAND]
```

### `providers list`

Display all 9 TTS providers with implementation status, health, and GPU mode.

```bash
atlas-vox providers list
```

**Output:**

```
                          TTS Providers
+-----------------+--------+-------------+------------------+----------+
| Name            | Type   | Implemented | Health           | GPU Mode |
+-----------------+--------+-------------+------------------+----------+
| Kokoro          | local  | OK          | OK 45ms          | host_cpu |
| Piper           | local  | OK          | OK 12ms          | host_cpu |
| ElevenLabs      | cloud  | OK          | OK 230ms         | --       |
| Azure AI Speech | cloud  | OK          | X timeout        | --       |
| Coqui XTTS v2  | local  | OK          | OK 890ms         | host_cpu |
| StyleTTS2       | local  | OK          | OK 1200ms        | host_cpu |
| CosyVoice       | local  | --          | --               | --       |
| Dia             | local  | OK          | OK 450ms         | host_cpu |
| Dia2            | local  | OK          | OK 520ms         | host_cpu |
+-----------------+--------+-------------+------------------+----------+
```

---

### `providers health`

Run a health check against a specific provider.

```bash
atlas-vox providers health NAME
```

| Argument | Type | Description |
|---|---|---|
| `NAME` | `str` | Provider name (e.g., `kokoro`, `elevenlabs`, `coqui_xtts`) |

**Examples:**

```bash
atlas-vox providers health kokoro
# OK kokoro: healthy (latency: 45ms)

atlas-vox providers health elevenlabs
# X elevenlabs: API key not configured

atlas-vox providers health unknown_provider
# X Unknown provider: unknown_provider
```

---

## presets -- Persona Presets

Manage reusable voice parameter presets (speed, pitch, volume).

```bash
atlas-vox presets [COMMAND]
```

### `presets list`

List all persona presets.

```bash
atlas-vox presets list
```

**Output:**

```
                    Persona Presets
+--------------+-------+-------+--------+--------+-------------------+
| Name         | Speed | Pitch | Volume | System | Description       |
+--------------+-------+-------+--------+--------+-------------------+
| Default      |  1.00 |    +0 |   1.00 | OK     | Standard settings |
| Narrator     |  0.90 |    -2 |   1.10 | OK     | Calm narration    |
| Energetic    |  1.20 |    +3 |   1.15 |        | Upbeat delivery   |
| Whisper      |  0.80 |    -5 |   0.60 |        | Soft, intimate    |
+--------------+-------+-------+--------+--------+-------------------+
```

System presets (marked with a checkmark) are built-in and cannot be deleted.

---

### `presets create`

Create a custom persona preset.

```bash
atlas-vox presets create [OPTIONS]
```

| Option | Type | Default | Description |
|---|---|---|---|
| `--name` | `str` | -- | Preset name (prompted if omitted) |
| `--speed` | `float` | `1.0` | Speech speed multiplier |
| `--pitch` | `float` | `0.0` | Pitch shift (semitones) |
| `--volume` | `float` | `1.0` | Volume multiplier |
| `--description` | `str` | `""` | Human-readable description |

**Example:**

```bash
atlas-vox presets create --name "Audiobook" --speed 0.85 --pitch -1 --volume 1.05 --description "Relaxed audiobook narration"
```

**Output:**

```
OK Preset created: Audiobook
```

---

## Shell Completions

Typer supports generating shell completions for Bash, Zsh, Fish, and PowerShell:

```bash
# Bash
atlas-vox --install-completion bash

# Zsh
atlas-vox --install-completion zsh

# Fish
atlas-vox --install-completion fish

# PowerShell
atlas-vox --install-completion powershell

# Show completion script without installing
atlas-vox --show-completion
```

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Application error (invalid input, resource not found, provider failure) |
| `2` | Usage error (missing argument, invalid option) |

All error messages are written to stderr with Rich formatting. Non-zero exit codes are set via `typer.Exit(1)`.

---

## Quick Reference Card

```
atlas-vox version                                 Show version
atlas-vox serve [--port N] [--mcp]                Start API server
atlas-vox init                                    Initialize system

atlas-vox profiles list                           List all profiles
atlas-vox profiles create --name NAME             Create profile
atlas-vox profiles delete PROFILE_ID              Delete profile

atlas-vox train upload PROFILE_ID DIRECTORY       Upload samples
atlas-vox train start PROFILE_ID [--provider P]   Start training
atlas-vox train status JOB_ID                     Check job status

atlas-vox synthesize TEXT -v PROFILE_ID [-o FILE]  Synthesize speech
atlas-vox compare TEXT -v ID1 -v ID2               Compare voices

atlas-vox providers list                          List providers
atlas-vox providers health NAME                   Health check

atlas-vox presets list                            List presets
atlas-vox presets create --name NAME              Create preset
```

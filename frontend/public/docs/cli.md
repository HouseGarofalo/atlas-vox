# CLI Reference

Atlas Vox includes a CLI built with Typer and Rich. Install with `pip install -e .` and run commands with the `atlas-vox` entry point.

```bash
atlas-vox --help
```

---

## synthesize

Synthesize text to speech and save the output audio file.

```
atlas-vox synthesize TEXT
```

### Options

| Flag | Description |
|------|-------------|
| `--provider, -p` | Provider name (default: kokoro) |
| `--voice, -v` | Voice ID |
| `--output, -o` | Output file path (default: output.wav) |
| `--format, -f` | Audio format: wav, mp3, ogg |
| `--speed` | Speed multiplier (0.5-2.0) |
| `--pitch` | Pitch adjustment (-20 to +20) |

### Example

```bash
atlas-vox synthesize "Hello world" -p kokoro -v af_heart -o hello.wav
```

---

## providers

List, inspect, and health-check TTS providers.

```
atlas-vox providers [SUBCOMMAND]
```

### Options

| Flag | Description |
|------|-------------|
| `list` | Show all providers with status |
| `health [NAME]` | Run health check on a provider |
| `config NAME` | Show provider configuration |

### Example

```bash
atlas-vox providers list
atlas-vox providers health kokoro
```

---

## profiles

Manage voice profiles.

```
atlas-vox profiles [SUBCOMMAND]
```

### Options

| Flag | Description |
|------|-------------|
| `list` | List all profiles |
| `create NAME --provider PROV` | Create a new profile |
| `show ID` | Show profile details |
| `delete ID` | Delete a profile |

### Example

```bash
atlas-vox profiles list
atlas-vox profiles create myvoice --provider kokoro
```

---

## train

Start a training job for a voice profile.

```
atlas-vox train PROFILE_ID
```

### Options

| Flag | Description |
|------|-------------|
| `--epochs, -e` | Number of training epochs (default: 100) |
| `--learning-rate, -lr` | Learning rate (default: 0.0001) |
| `--batch-size, -b` | Batch size (default: 4) |
| `--wait, -w` | Wait for training to complete |

### Example

```bash
atlas-vox train abc-123 --epochs 200 --wait
```

---

## compare

Synthesize the same text with multiple profiles for comparison.

```
atlas-vox compare TEXT --profiles ID1 ID2 [ID3...]
```

### Options

| Flag | Description |
|------|-------------|
| `--profiles` | Comma-separated profile IDs (2-5) |
| `--output-dir, -o` | Directory to save audio files |

### Example

```bash
atlas-vox compare "Test phrase" --profiles id1,id2,id3 -o ./comparison/
```

---

## presets

Manage synthesis presets (persona parameter sets).

```
atlas-vox presets [SUBCOMMAND]
```

### Options

| Flag | Description |
|------|-------------|
| `list` | Show all presets |
| `show NAME` | Show preset details |

### Example

```bash
atlas-vox presets list
```

---

## init

Initialize the Atlas Vox database and default configuration.

```
atlas-vox init
```

### Options

| Flag | Description |
|------|-------------|
| `--force` | Re-initialize even if database exists |

### Example

```bash
atlas-vox init --force
```

---

## serve

Start the Atlas Vox API server (alternative to uvicorn).

```
atlas-vox serve
```

### Options

| Flag | Description |
|------|-------------|
| `--host` | Bind address (default: 0.0.0.0) |
| `--port` | Port number (default: 8100) |
| `--reload` | Enable auto-reload for development |
| `--workers` | Number of worker processes |

### Example

```bash
atlas-vox serve --port 8100 --reload
```

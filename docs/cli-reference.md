# Atlas Vox CLI Reference

## Installation

```bash
pip install -e ./backend
```

Entry point: `atlas-vox`

## Commands

### `atlas-vox init`
Initialize Atlas Vox: create storage directories, check system dependencies, initialize database.

### `atlas-vox serve`
Start the API server.
```bash
atlas-vox serve --host 0.0.0.0 --port 8000 --mcp
```

### `atlas-vox version`
Show version information.

### `atlas-vox profiles`
```bash
atlas-vox profiles list                           # List all profiles (Rich table)
atlas-vox profiles create --name "My Voice" --provider kokoro
atlas-vox profiles delete <profile_id>
```

### `atlas-vox train`
```bash
atlas-vox train upload <profile_id> ./audio/       # Upload samples from directory
atlas-vox train start <profile_id>                 # Start training job
atlas-vox train start <profile_id> --provider coqui_xtts  # Override provider
atlas-vox train status <job_id>                    # Check training status
```

### `atlas-vox synthesize`
```bash
atlas-vox synthesize "Hello world" --voice <profile_id> --output hello.wav
atlas-vox synthesize "Hello world" -v <id> -o out.mp3 --format mp3 --play
atlas-vox synthesize "Fast speech" -v <id> --speed 1.5
```

### `atlas-vox providers`
```bash
atlas-vox providers list                           # List all 9 providers with health
atlas-vox providers health kokoro                  # Check single provider
```

### `atlas-vox compare`
```bash
atlas-vox compare "Hello" -v <id1> -v <id2>       # Compare two voices
```

### `atlas-vox presets`
```bash
atlas-vox presets list                             # List persona presets
atlas-vox presets create --name "Whisper" --speed 0.7 --pitch -10 --volume 0.6
```

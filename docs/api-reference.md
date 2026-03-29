# Atlas Vox API Reference

Base URL: `http://localhost:8100/api/v1`

Interactive docs: `http://localhost:8100/docs` (Swagger) | `http://localhost:8100/redoc` (ReDoc)

## Endpoints

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |

### Profiles
| Method | Path | Description |
|--------|------|-------------|
| GET | `/profiles` | List all profiles |
| POST | `/profiles` | Create profile |
| GET | `/profiles/{id}` | Get profile |
| PUT | `/profiles/{id}` | Update profile |
| DELETE | `/profiles/{id}` | Delete profile |
| GET | `/profiles/{id}/versions` | List model versions |
| POST | `/profiles/{id}/activate-version/{vid}` | Activate version |

### Samples
| Method | Path | Description |
|--------|------|-------------|
| POST | `/profiles/{id}/samples` | Upload audio files (multipart) |
| GET | `/profiles/{id}/samples` | List samples |
| DELETE | `/profiles/{id}/samples/{sid}` | Delete sample |
| GET | `/profiles/{id}/samples/{sid}/analysis` | Audio analysis |
| POST | `/profiles/{id}/samples/preprocess` | Queue preprocessing |

### Training
| Method | Path | Description |
|--------|------|-------------|
| POST | `/profiles/{id}/train` | Start training job |
| GET | `/training/jobs` | List jobs (filter: `?profile_id=&status=`) |
| GET | `/training/jobs/{id}` | Job status with Celery progress |
| POST | `/training/jobs/{id}/cancel` | Cancel job |
| WS | `/training/jobs/{id}/progress` | WebSocket live progress |

### Synthesis
| Method | Path | Description |
|--------|------|-------------|
| POST | `/synthesize` | Synthesize text → audio URL |
| POST | `/synthesize/stream` | Streaming synthesis (chunked) |
| POST | `/synthesize/batch` | Batch multi-line synthesis |
| GET | `/synthesis/history` | Synthesis history |
| GET | `/audio/{filename}` | Serve audio files |

### Comparison
| Method | Path | Description |
|--------|------|-------------|
| POST | `/compare` | Side-by-side multi-voice comparison |

### Providers
| Method | Path | Description |
|--------|------|-------------|
| GET | `/providers` | List all 9 providers |
| GET | `/providers/{name}` | Provider details + capabilities |
| POST | `/providers/{name}/health` | Run health check |
| GET | `/providers/{name}/voices` | List provider voices |

### Presets
| Method | Path | Description |
|--------|------|-------------|
| GET | `/presets` | List presets (seeds 6 defaults) |
| POST | `/presets` | Create custom preset |
| PUT | `/presets/{id}` | Update preset |
| DELETE | `/presets/{id}` | Delete preset (custom only) |

### API Keys
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api-keys` | Create key (shown once) |
| GET | `/api-keys` | List keys (masked) |
| DELETE | `/api-keys/{id}` | Revoke key |

### Webhooks
| Method | Path | Description |
|--------|------|-------------|
| GET | `/webhooks` | List webhooks |
| POST | `/webhooks` | Create webhook |
| PUT | `/webhooks/{id}` | Update webhook |
| DELETE | `/webhooks/{id}` | Delete webhook |
| POST | `/webhooks/{id}/test` | Send test payload |

### MCP
| Method | Path | Description |
|--------|------|-------------|
| GET | `/mcp/sse` | SSE transport |
| POST | `/mcp/message` | JSONRPC 2.0 messages |

"""Download model weights from HuggingFace for each GPU provider.

Run this script before starting the service so that models are cached
locally and the first synthesis call does not block on a download.

Usage:
    python scripts/download_models.py [--provider NAME] [--all] [--cache-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Model registry — maps provider name to HuggingFace repo ID(s)
# ---------------------------------------------------------------------------

MODELS: dict[str, list[str]] = {
    "fish_speech": ["fishaudio/fish-speech-1.5"],
    "chatterbox": ["resemble-ai/chatterbox"],
    "f5_tts": ["SWivid/F5-TTS"],
    "openvoice_v2": ["myshell-ai/OpenVoiceV2"],
    "orpheus": ["canopylabs/orpheus-3b-0.1-ft"],
}


def download_model(repo_id: str, cache_dir: str | None = None) -> None:
    """Download a single model from HuggingFace Hub."""
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("ERROR: huggingface_hub is not installed. Run: pip install huggingface_hub", file=sys.stderr)
        sys.exit(1)

    kwargs: dict = {"repo_id": repo_id}
    if cache_dir:
        kwargs["cache_dir"] = cache_dir

    print(f"  Downloading {repo_id} ...")
    path = snapshot_download(**kwargs)
    print(f"  Cached at: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download GPU provider model weights")
    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        help="Download models for a specific provider (e.g. fish_speech)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=False,
        help="Download models for ALL providers",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=None,
        help="Custom HuggingFace cache directory",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        default=False,
        help="List available providers and their models",
    )
    args = parser.parse_args()

    if args.list:
        print("Available providers and models:")
        for name, repos in MODELS.items():
            for repo in repos:
                print(f"  {name:20s} -> {repo}")
        return

    if not args.provider and not args.all:
        parser.print_help()
        print("\nSpecify --provider NAME or --all to download models.")
        return

    targets: dict[str, list[str]] = {}
    if args.all:
        targets = MODELS
    elif args.provider:
        if args.provider not in MODELS:
            print(f"ERROR: Unknown provider '{args.provider}'. Known: {', '.join(MODELS)}", file=sys.stderr)
            sys.exit(1)
        targets = {args.provider: MODELS[args.provider]}

    for provider_name, repos in targets.items():
        print(f"\n[{provider_name}]")
        for repo_id in repos:
            try:
                download_model(repo_id, cache_dir=args.cache_dir)
            except Exception as exc:
                print(f"  FAILED: {exc}", file=sys.stderr)

    print("\nDone.")


if __name__ == "__main__":
    main()

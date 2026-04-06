"""Download Kokoro TTS model and default voice files for Docker builds."""

import os
import time
import urllib.request

BASE_URL = "https://huggingface.co/hexgrad/Kokoro-82M/resolve/main/"
_home = os.environ.get("HOME", "/home/app")
CACHE_DIR = f"{_home}/.cache/huggingface/hub/models--hexgrad--Kokoro-82M/snapshots/main/"

MODEL_FILES = [
    ("kokoro-v1_0.pth", os.path.join(CACHE_DIR, "kokoro-v1_0.pth")),
    ("config.json", os.path.join(CACHE_DIR, "config.json")),
]

VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "af_alloy",
    "am_adam", "am_michael", "am_echo",
    "bf_emma", "bf_alice", "bm_george", "bm_lewis", "bm_daniel",
]


def main():
    os.makedirs(os.path.join(CACHE_DIR, "voices"), exist_ok=True)

    all_files = list(MODEL_FILES)
    all_files += [
        (f"voices/{v}.pt", os.path.join(CACHE_DIR, f"voices/{v}.pt"))
        for v in VOICES
    ]

    for url_path, dest in all_files:
        for attempt in range(3):
            try:
                urllib.request.urlretrieve(BASE_URL + url_path, dest)
                print(f"Downloaded {url_path}")
                break
            except Exception as e:
                print(f"Attempt {attempt + 1}/3 failed for {url_path}: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    print(f"WARNING: Could not download {url_path}")

    print("Kokoro model + voices download complete")


if __name__ == "__main__":
    main()

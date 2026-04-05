"""Download default Piper model (English, medium quality) for Docker builds."""

import os
import time
import urllib.request

MODEL_DIR = "storage/models/piper"
BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/"

FILES = [
    ("en_US-lessac-medium.onnx", os.path.join(MODEL_DIR, "en_US-lessac-medium.onnx")),
    ("en_US-lessac-medium.onnx.json", os.path.join(MODEL_DIR, "en_US-lessac-medium.onnx.json")),
]


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    for fname, dest in FILES:
        for attempt in range(3):
            try:
                urllib.request.urlretrieve(BASE_URL + fname, dest)
                print(f"Downloaded {fname}")
                break
            except Exception as e:
                print(f"Attempt {attempt + 1}/3 failed for {fname}: {e}")
                if attempt < 2:
                    time.sleep(5)
                else:
                    print(f"WARNING: Could not download {fname}")

    print("Piper model download complete")


if __name__ == "__main__":
    main()

"""Runtime configuration for the TrashTag service. Every value is env-overridable."""

import os

# Loopback by default. The dashboard is an internal ops tool; bind to 0.0.0.0 only on a
# network you trust.
HOST: str = os.getenv("TRASHTAG_HOST", "127.0.0.1")
PORT: int = int(os.getenv("TRASHTAG_PORT", "8000"))
ENV: str = os.getenv("TRASHTAG_ENV", "dev")

# Auto-reload only in dev — never hot-reload a production process.
RELOAD: bool = ENV == "dev"

# Detector selection: "stub" (default, deterministic) or "vlm" (local vision LLM)
DETECTOR: str = os.getenv("TRASHTAG_DETECTOR", "stub")

# Frame-dedup gate: Hamming distance (out of 64) below which two video frames count as the
# same scene and the later one skips the detector. Lower = more sensitive (more detector calls).
FRAME_THRESHOLD: int = int(os.getenv("TRASHTAG_FRAME_THRESHOLD", "10"))

# VLM detector config (Ollama by default, OpenAI-compatible endpoint)
VLM_HOST: str = os.getenv("TRASHTAG_VLM_HOST", "localhost")
VLM_PORT: int = int(os.getenv("TRASHTAG_VLM_PORT", "11434"))
VLM_PATH: str = os.getenv("TRASHTAG_VLM_PATH", "/v1")
VLM_MODEL: str = os.getenv("TRASHTAG_VLM_MODEL", "llama3.2-vision")
VLM_API_KEY: str = os.getenv("TRASHTAG_VLM_API_KEY", "")

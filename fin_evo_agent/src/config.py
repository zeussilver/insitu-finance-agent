"""Global configuration for the Yunjue Agent system."""

import os
from pathlib import Path

# Project root directory
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"

# Load .env file if exists
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

# Database configuration
DB_PATH = DATA_DIR / "db" / "evolution.db"
DB_URL = f"sqlite:///{DB_PATH}"

# Storage paths
ARTIFACTS_DIR = DATA_DIR / "artifacts"
BOOTSTRAP_DIR = ARTIFACTS_DIR / "bootstrap"
GENERATED_DIR = ARTIFACTS_DIR / "generated"
CACHE_DIR = DATA_DIR / "cache"
LOGS_DIR = DATA_DIR / "logs"

# Ensure directories exist
for p in [BOOTSTRAP_DIR, GENERATED_DIR, CACHE_DIR, LOGS_DIR, DB_PATH.parent]:
    p.mkdir(parents=True, exist_ok=True)

# LLM Configuration (Qwen3 via DashScope OpenAI-compatible API)
LLM_API_KEY = os.getenv("API_KEY", "")
LLM_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
LLM_MODEL = "qwen3-max-2026-01-23"
LLM_TEMPERATURE = 0.1
LLM_ENABLE_THINKING = True

# Execution limits
EXECUTION_TIMEOUT_SEC = 30
EXECUTION_MEMORY_MB = 512

import os
from pathlib import Path
def load_env():
    """Tiny .env loader (no extra dependency). Real environment variables win; empty values are ignored."""
    for p in (Path(__file__).resolve().parent / ".env", Path(__file__).resolve().parent.parent / ".env"):
        if p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    if v.strip(): os.environ.setdefault(k.strip(), v.strip())

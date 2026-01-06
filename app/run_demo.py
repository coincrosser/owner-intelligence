from __future__ import annotations

from pathlib import Path

from app.pipeline.runner import run_pipeline


if __name__ == "__main__":
    run_pipeline(Path("app/sample_data"))

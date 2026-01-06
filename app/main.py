from __future__ import annotations

import argparse
from pathlib import Path

from app.pipeline.runner import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Owner intelligence pipeline")
    parser.add_argument(
        "--sample-dir",
        type=Path,
        default=Path("app/sample_data"),
        help="Directory containing sample data",
    )
    args = parser.parse_args()
    run_pipeline(args.sample_dir)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3

"""Build and package the ingestion collector AWS Lambda deployment zip."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BUILD_DIR = PROJECT_ROOT / "build" / "lambda"
DEFAULT_OUTPUT_ZIP = PROJECT_ROOT / "dist" / "collector_lambda.zip"
DEFAULT_REQUIREMENTS = PROJECT_ROOT / "collector" / "lambda_requirements.txt"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--build-dir",
        type=Path,
        default=DEFAULT_BUILD_DIR,
        help="Temporary directory to assemble dependencies and source files.",
    )
    parser.add_argument(
        "--output-zip",
        type=Path,
        default=DEFAULT_OUTPUT_ZIP,
        help="Destination path for the Lambda deployment zip archive.",
    )
    parser.add_argument(
        "--requirements",
        type=Path,
        default=DEFAULT_REQUIREMENTS,
        help="Path to requirements.txt for Lambda packaging.",
    )
    parser.add_argument(
        "--skip-pip",
        action="store_true",
        help="Skip pip install and only repackage collector source files.",
    )
    return parser.parse_args()


def compute_sha256(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def package_lambda(
    build_dir: Path,
    output_zip: Path,
    requirements: Path,
    skip_pip: bool = False,
) -> Path:
    build_dir.mkdir(parents=True, exist_ok=True)
    output_zip.parent.mkdir(parents=True, exist_ok=True)

    if not skip_pip:
        print(f"Installing dependencies from {requirements} into {build_dir}...")
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            str(build_dir),
            "-r",
            str(requirements),
            "--no-compile",
            "--upgrade",
            "--quiet",
        ]
        subprocess.run(cmd, check=True)

    # Copy source files into package root
    source_files = [
        PROJECT_ROOT / "collector" / "collect_raw_data.py",
        PROJECT_ROOT / "collector" / "lambda_handler.py",
    ]
    for src in source_files:
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        dest = build_dir / src.name
        shutil.copy2(src, dest)
        print(f"Copied {src.name} to {dest}")

    # Remove __pycache__ directories and *.pyc files
    for pycache in build_dir.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    for pyc in build_dir.rglob("*.pyc"):
        pyc.unlink(missing_ok=True)

    print(f"Creating zip archive at {output_zip}...")
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zip_out:
        for file_path in build_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(build_dir)
                zip_out.write(file_path, arcname)

    size_mb = output_zip.stat().st_size / (1024 * 1024)
    sha256 = compute_sha256(output_zip)
    print(
        f"Successfully packaged {output_zip.name}: {size_mb:.2f} MB (SHA256: {sha256[:16]}...)"
    )
    return output_zip


def main() -> None:
    args = parse_args()
    package_lambda(
        build_dir=args.build_dir,
        output_zip=args.output_zip,
        requirements=args.requirements,
        skip_pip=args.skip_pip,
    )


if __name__ == "__main__":
    main()

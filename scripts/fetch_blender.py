# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Fetch the pinned official Blender archive for contributor verification."""
import argparse
import hashlib
from pathlib import Path
import shutil
import tempfile
import urllib.request


OFFICIAL_BASE_URLS = (
    "https://download.blender.org/release/Blender4.5/",
    "https://mirror.blender.org/release/Blender4.5/",
)


class DownloadError(RuntimeError):
    pass


def fetch_archive(folder, name, expected_sha256, *, opener=None):
    if Path(name).name != name:
        raise ValueError("Archive must be a filename")
    if len(expected_sha256) != 64 or any(c not in "0123456789abcdef" for c in expected_sha256):
        raise ValueError("A pinned SHA-256 is required")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    archive = folder / name
    if archive.exists():
        raise FileExistsError(archive)
    opener = opener or urllib.request.urlopen
    failures = []
    for base_url in OFFICIAL_BASE_URLS:
        url = base_url + name
        try:
            with tempfile.TemporaryDirectory(prefix="download-", dir=folder) as temporary:
                downloaded = Path(temporary) / name
                request = urllib.request.Request(
                    url, headers={"User-Agent": "OpenTokyoWorld/1.0 (contributor verification)"})
                with opener(request, timeout=120) as response, downloaded.open("xb") as output:
                    if not response.geturl().startswith("https://"):
                        raise DownloadError("Blender archive source must use HTTPS")
                    print("Official Blender source:", response.geturl())
                    shutil.copyfileobj(response, output, 1024 * 1024)
                with downloaded.open("rb") as handle:
                    actual = hashlib.file_digest(handle, "sha256").hexdigest()
                if actual != expected_sha256:
                    raise DownloadError(
                        f"Blender archive checksum mismatch: expected {expected_sha256}, got {actual}")
                downloaded.replace(archive)
            return archive
        except (OSError, DownloadError) as error:
            message = f"{url}: {error}"
            failures.append(message)
            print("Blender archive attempt failed:", message)
    raise DownloadError("All official Blender archive sources failed:\n" + "\n".join(failures))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--archive", required=True)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args()
    fetch_archive(args.folder, args.archive, args.sha256)


if __name__ == "__main__":
    main()

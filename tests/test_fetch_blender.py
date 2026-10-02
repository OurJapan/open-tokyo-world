# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import contextlib
import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("fetch_blender", ROOT / "scripts/fetch_blender.py")
fetch_blender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fetch_blender)


class Response(io.BytesIO):
    def __init__(self, data, url):
        super().__init__(data)
        self.url = url

    def geturl(self):
        return self.url


class BlenderArchiveDownload(unittest.TestCase):
    def setUp(self):
        self.name = "blender-4.5.1-linux-x64.tar.xz"
        self.data = b"verified archive fixture"
        self.sha256 = hashlib.sha256(self.data).hexdigest()
        self.calls = []

    def run_fetch(self, folder, responses):
        def opener(request, timeout):
            self.calls.append(request.full_url)
            self.assertEqual(timeout, 120)
            response = responses[len(self.calls) - 1]
            if isinstance(response, Exception):
                raise response
            data, url = response
            return Response(data, url or request.full_url)

        with contextlib.redirect_stdout(io.StringIO()):
            return fetch_blender.fetch_archive(folder, self.name, self.sha256, opener=opener)

    def test_verified_primary_archive_is_retained(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = self.run_fetch(folder, [(self.data, None)])
            self.assertEqual(archive.read_bytes(), self.data)
            self.assertEqual(list(Path(folder).iterdir()), [archive])
        self.assertEqual(self.calls, [fetch_blender.OFFICIAL_BASE_URLS[0] + self.name])

    def test_checksum_mismatch_falls_back_without_retaining_bad_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = self.run_fetch(folder, [(b"truncated", None), (self.data, None)])
            self.assertEqual(archive.read_bytes(), self.data)
            self.assertEqual(list(Path(folder).iterdir()), [archive])
        self.assertEqual(self.calls, [base + self.name for base in fetch_blender.OFFICIAL_BASE_URLS])

    def test_network_failure_falls_back(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = self.run_fetch(folder, [TimeoutError("timeout"), (self.data, None)])
            self.assertEqual(archive.read_bytes(), self.data)
        self.assertEqual(len(self.calls), 2)

    def test_all_checksum_failures_stop_without_retaining_an_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(fetch_blender.DownloadError, self.sha256):
                self.run_fetch(folder, [(b"bad primary", None), (b"bad mirror", None)])
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_insecure_redirect_is_rejected_before_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = self.run_fetch(folder, [(self.data, "http://mirror.example/archive"), (self.data, None)])
            self.assertEqual(archive.read_bytes(), self.data)
        self.assertEqual(len(self.calls), 2)

    def test_existing_archive_is_preserved_without_download(self):
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / self.name
            archive.write_bytes(b"existing archive")
            with self.assertRaises(FileExistsError):
                self.run_fetch(folder, [])
            self.assertEqual(archive.read_bytes(), b"existing archive")
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()

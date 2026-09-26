# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("city_images", ROOT / "scripts/verify_city_images.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
URL = audit.DATASETS["minato-2025-lod3"] + "data/data221.b3dm"


def b3dm(image=b"encoded-texture", change=None):
    doc = {"asset": {"version": "2.0"}, "buffers": [{"byteLength": len(image)}],
           "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": len(image)}],
           "images": [{"mimeType": "image/webp", "bufferView": 0}]}
    if change:
        change(doc)
    raw = json.dumps(doc).encode()
    raw += b" " * (-len(raw) % 4)
    binary = image + b"\0" * (-len(image) % 4)
    glb = (struct.pack("<4sII", b"glTF", 2, 28 + len(raw) + len(binary)) +
           struct.pack("<II", len(raw), 0x4E4F534A) + raw + struct.pack("<II", len(binary), 0x004E4942) + binary)
    feature = b'{"BATCH_LENGTH":1}   '
    return struct.pack("<4s6I", b"b3dm", 1, 28 + len(feature) + len(glb), len(feature), 0, 0, 0) + feature + glb


def image_record(name="image", packed=None, urls=(URL,), source="FILE"):
    return {"image": name, "packed_sha256": packed, "source_type": source,
            "material_object_uses": [{"object": "building", "source_url_claim": u} for u in urls]}


class ImageProvenanceTests(unittest.TestCase):
    def test_hashes_encoded_bytes_not_padding(self):
        records = audit.embedded_images(b3dm(b"image-bytes"))
        self.assertEqual(records, [{"index": 0, "mime_type": "image/webp", "bytes": 11, "sha256": audit.sha(b"image-bytes")}])

    def test_short_or_bad_headers_rejected(self):
        raw = b3dm()
        for invalid in (b"", raw[:27], b"BAD!" + raw[4:], raw[:-1], raw + b"padding"):
            with self.subTest(length=len(invalid)), self.assertRaises((ValueError, struct.error)):
                audit.embedded_images(invalid)

    def test_external_images_and_negative_views_rejected(self):
        changes = [lambda d: d["images"][0].update(uri="https://example.invalid/image"),
                   lambda d: d["images"][0].update(bufferView=-1),
                   lambda d: d["bufferViews"][0].update(byteOffset=-1),
                   lambda d: d["bufferViews"][0].update(byteLength=99999),
                   lambda d: d["bufferViews"][0].update(buffer=1),
                   lambda d: d["buffers"][0].update(uri="external.bin")]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(ValueError):
                audit.embedded_images(b3dm(change=change))

    def test_image_cannot_reference_glb_padding(self):
        with self.assertRaises(ValueError):
            audit.embedded_images(b3dm(b"x", lambda d: d["bufferViews"][0].update(byteLength=4)))

    def test_only_reviewed_urls_can_be_requested(self):
        self.assertEqual(audit.source_dataset(URL), "minato-2025-lod3")
        for url in (URL.replace("https:", "http:"), URL + "?token=anything", URL + "/../secret", URL.replace("reearth.io", "example.invalid"), "file:///etc/passwd"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                audit.source_dataset(url)
        with self.assertRaises(ValueError):
            audit.ExactRedirect().redirect_request(None, None, 302, "", {}, URL)

    def test_download_budget_is_enforced(self):
        budget = audit.DownloadBudget(8)
        budget.consume(8)
        with self.assertRaises(ValueError):
            budget.consume(1)

    def test_fresh_source_receipt_can_be_rechecked_offline(self):
        class Response(io.BytesIO):
            def geturl(self):
                return URL
        raw = b3dm()
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(audit.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value = Response(raw)
                record = audit.get_source(URL, Path(folder), True, audit.DownloadBudget())
            with patch.object(audit.urllib.request, "build_opener") as opener:
                checked = audit.get_source(URL, Path(folder), False, audit.DownloadBudget(), record)
                opener.assert_not_called()
            self.assertEqual(record, checked)
            self.assertEqual(record["sha256"], audit.sha(raw))

    def test_corrupted_cache_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            cache = Path(folder)
            key = audit.sha(URL.encode())
            (cache / (key + ".b3dm")).write_bytes(b"bad")
            audit.write_new_json(cache / (key + ".json"), {"url": URL, "bytes": 3, "sha256": audit.sha(b"old")})
            with patch.object(audit.urllib.request, "build_opener") as opener:
                with self.assertRaisesRegex(ValueError, "differs from receipt"):
                    audit.get_source(URL, cache, True, audit.DownloadBudget())
                opener.assert_not_called()
            self.assertEqual((cache / (key + ".b3dm")).read_bytes(), b"bad")

    def test_changed_upstream_does_not_install_when_locked(self):
        class Response(io.BytesIO):
            def geturl(self):
                return URL
        raw = b3dm()
        with tempfile.TemporaryDirectory() as folder, patch.object(audit.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = Response(raw)
            with self.assertRaisesRegex(ValueError, "differs from the source lock"):
                audit.get_source(URL, Path(folder), True, audit.DownloadBudget(), {"bytes": len(raw), "sha256": "0" * 64})
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_identity_does_not_grant_redistribution(self):
        image_hash = audit.sha(b"picture")
        inventory = {"images": [image_record(packed=image_hash), image_record("atlas", image_hash + "x", ()),
                                 image_record("Render Result", None, (), "VIEWER")]}
        records = audit.compare_images(inventory, {URL: {"ok": True, "images": [{"sha256": image_hash}]}})
        self.assertEqual([r["status"] for r in records], ["matched-claimed-source", "unresolved-no-source", "runtime-only"])
        self.assertTrue(all(r["redistribution"] == "pending-separate-review" for r in records))

    def test_wrong_source_mapping_and_missing_source_are_explicit(self):
        image_hash = audit.sha(b"picture")
        other = URL.replace("data221.b3dm", "data222.b3dm")
        inventory = {"images": [image_record(packed=image_hash)]}
        records = audit.compare_images(inventory, {other: {"ok": True, "images": [{"sha256": image_hash}]}})
        self.assertEqual(records[0]["status"], "matched-other-source-review-mapping")
        self.assertEqual(audit.compare_images(inventory, {})[0]["status"], "source-unavailable")
        self.assertEqual(audit.compare_images(inventory, {URL: {"ok": True, "images": []}})[0]["status"], "content-mismatch")


if __name__ == "__main__":
    unittest.main()

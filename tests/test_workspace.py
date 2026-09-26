# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("contributor_workspace", ROOT / "scripts/workspace.py")
workspace = importlib.util.module_from_spec(spec)
spec.loader.exec_module(workspace)


def expected(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


class WorkspaceContract(unittest.TestCase):
    def test_full_city_is_not_claimed_public_or_substituted(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stderr(io.StringIO()) as errors:
            with patch.object(workspace, "setup_mori") as build, patch.object(workspace, "find_blender") as blender:
                code = workspace.main(["setup", "--workspace", folder])
            self.assertEqual(code, 1)
            self.assertIn("Full city is unavailable", errors.getvalue())
            build.assert_not_called()
            blender.assert_not_called()
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_catalog_sources_match_executed_importer(self):
        tile_spec = importlib.util.spec_from_file_location("workspace_tile", ROOT / "starter/plateau/tile.py")
        tile = importlib.util.module_from_spec(tile_spec)
        tile_spec.loader.exec_module(tile)
        catalog = workspace.load_catalog()
        for name, (url, size, sha) in tile.FILES.items():
            self.assertEqual(catalog["sources"]["plateau-minato-2025"]["files"][name], {"url": url, "bytes": size, "sha256": sha})
        evidence = workspace.read_json(ROOT / catalog["profiles"]["city"]["evidence"])
        self.assertEqual(catalog["profiles"]["city"]["asset"]["sha256"], evidence["output_blends"]["after.blend"])
        self.assertIsNone(catalog["profiles"]["city"]["public_url"])

    def test_import_rejects_wrong_scene_before_blender(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scene = root / "wrong.blend"
            scene.write_bytes(b"not the city")
            with patch.object(workspace, "blender_check") as check:
                with self.assertRaisesRegex(ValueError, "Pinned file mismatch"):
                    workspace.import_city(root / "workspace", scene, Path("blender"), workspace.load_catalog())
                check.assert_not_called()
            self.assertFalse((root / "workspace").exists())

    def test_existing_wrong_destination_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, target = root / "source", root / "target"
            source.write_bytes(b"approved")
            target.write_bytes(b"keep this")
            with self.assertRaises(ValueError):
                workspace.copy_verified(source, target, expected(b"approved"))
            self.assertEqual(target.read_bytes(), b"keep this")
            self.assertEqual(source.read_bytes(), b"approved")

    def test_bad_download_is_not_installed(self):
        class Response(io.BytesIO):
            pass
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "sources/source.json"
            with patch.object(workspace.urllib.request, "build_opener") as opener:
                opener.return_value.open.return_value = Response(b"bad")
                with self.assertRaisesRegex(ValueError, "Downloaded source differs"):
                    workspace.fetch_file(target, {**expected(b"good"), "url": "https://example.invalid/data"})
            self.assertFalse(target.exists())

    def test_corrupt_cached_source_does_not_fall_back_to_download(self):
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder) / "data"
            target.write_bytes(b"bad")
            with patch.object(workspace.urllib.request, "build_opener") as opener:
                with self.assertRaises(ValueError):
                    workspace.fetch_file(target, {**expected(b"good"), "url": "https://example.invalid/data"})
                opener.assert_not_called()
            self.assertEqual(target.read_bytes(), b"bad")

    def test_http_and_downgrade_redirect_rejected(self):
        with self.assertRaises(ValueError):
            workspace.fetch_file(Path("not-created"), {**expected(b"x"), "url": "http://example.invalid/data"})
        with self.assertRaises(ValueError):
            workspace.HTTPSRedirects().redirect_request(None, None, 302, "", {}, "http://example.invalid/data")

    def test_record_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as folder:
            for relative in ("../outside", "/outside", "C:/outside", "sub/../../outside", "..\\outside", ""):
                with self.subTest(relative=relative), self.assertRaises(ValueError):
                    workspace.inside(Path(folder), relative)

    def test_corrupt_registered_asset_blocks_edit(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "scene.blend").write_bytes(b"good")
            workspace.save_profile(root, "mori", {"scene": "scene.blend", "files": {"scene.blend": expected(b"good")}})
            (root / "scene.blend").write_bytes(b"edit")
            with self.assertRaises(ValueError):
                workspace.prepare_edit(root, "mori", workspace.load_catalog())
            self.assertFalse((root / "edits").exists())

    def test_edit_is_a_new_copy_and_carries_attribution(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            scene, notice = root / "scene.blend", root / "NOTICE.md"
            scene.write_bytes(b"good")
            notice.write_text("attribution", encoding="utf8")
            workspace.save_profile(root, "mori", {"scene": "scene.blend", "files": workspace.file_specs(root, [scene, notice])})
            first = workspace.prepare_edit(root, "mori", workspace.load_catalog())
            second = workspace.prepare_edit(root, "mori", workspace.load_catalog())
            self.assertNotEqual(first, second)
            first.write_bytes(b"changed")
            self.assertEqual(scene.read_bytes(), b"good")
            self.assertEqual(second.read_bytes(), b"good")
            self.assertEqual((first.parent / "NOTICE.md").read_text(), "attribution")
            self.assertFalse(workspace.read_json(first.parent / "edit.json")["validated_edit"])

    def test_wrong_blender_version_stops_before_probe(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(workspace.subprocess, "run") as run:
            run.return_value.stdout = "Blender 4.5.2 LTS\n"
            with self.assertRaisesRegex(ValueError, "version mismatch"):
                workspace.blender_check(Path(folder), Path("blender"), workspace.load_catalog())
            self.assertEqual(run.call_count, 1)
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_failed_or_incomplete_build_does_not_register_a_scene(self):
        reports = [
            {"ok": False},
            {"ok": True, "licensed_parts_verified": False},
            {"ok": True, "licensed_parts_verified": True,
             "validation": {"before": {"ok": False}, "after": {"ok": True, "meshes": 42}}},
            {"ok": True, "licensed_parts_verified": True,
             "validation": {"before": {"ok": True}, "after": {"ok": True, "meshes": 41}}},
            {"ok": True, "licensed_parts_verified": True,
             "validation": {"before": {"ok": True}, "after": {"ok": True, "meshes": 42}}},
        ]
        for report in reports:
            with self.subTest(report=report), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)

                def generate(command, **kwargs):
                    output = Path(command[command.index("--output") + 1])
                    workspace.write_json(output / "run.json", report)

                with patch.object(workspace, "blender_check"), patch.object(workspace, "fetch_sources", return_value=root), \
                     patch.object(workspace.subprocess, "run", side_effect=generate), contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaises(ValueError):
                        workspace.setup_mori(root, Path("blender"), workspace.load_catalog())
                self.assertFalse((root / "workspace.json").exists())


if __name__ == "__main__":
    unittest.main()

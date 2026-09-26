# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import contextlib
import copy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import district_distribution as dist


def pin(data, urls=None):
    result = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    if urls is not None:
        result["urls"] = urls
    return result


def fixture():
    packages = {}
    for key in ("alpha", "beta", "trees"):
        packages[key] = {"version": "1.0.0", "kind": "shared" if key == "trees" else "source",
                         "requires": [] if key == "trees" else ["trees"], "availability": "public",
                         "license": "synthetic test data", "notice": "Fixture only",
                         "files": {key + ".bin": pin(key.encode(), ["https://example.invalid/" + key])}}
    districts = {key: {"label": key, "version": "1.0.0", "packages": [key], "input_package": key,
                       "adapter": "blend-package-v1", "scope": "synthetic fixture, not a real district",
                       "frame": "fixture", "recipe_files": []} for key in ("alpha", "beta")}
    return {"schema_version": 1, "runtime": {"blender_version": "4.5.1", "runner_python_versions": [[3, 11], [3, 12]]},
            "packages": packages, "districts": districts,
            "tool_files": ["scripts/district_distribution.py", "scripts/workspace.py", "scripts/workspace_blender.py"]}


def write_sources(root, catalog):
    for key, package in catalog["packages"].items():
        for name in package["files"]:
            path = root / key / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(key.encode())


class DistrictDistributionContracts(unittest.TestCase):
    def test_selects_only_requested_district_and_deduplicates_shared_dependencies(self):
        catalog = fixture()
        one = dist.plan(catalog, ["alpha"], [])
        self.assertEqual(set(one["packages"]), {"alpha", "trees"})
        both = dist.plan(catalog, ["beta", "alpha", "alpha"], ["trees"])
        again = dist.plan(catalog, ["alpha", "beta"], ["trees"])
        self.assertEqual(both, again)
        self.assertEqual(set(both["packages"]), {"alpha", "beta", "trees"})
        self.assertEqual(dist.build_identity(one, "alpha"), dist.build_identity(both, "alpha"))

    def test_cycles_missing_dependencies_and_unknown_districts_stop(self):
        catalog = fixture()
        with self.assertRaisesRegex(ValueError, "Unknown district"):
            dist.plan(catalog, ["city"], [])
        catalog["packages"]["trees"]["requires"] = ["alpha"]
        with self.assertRaisesRegex(ValueError, "cycle"):
            dist.plan(catalog, ["alpha"], [])
        catalog["packages"]["trees"]["requires"] = ["missing"]
        with self.assertRaisesRegex(ValueError, "Unknown package dependency"):
            dist.plan(catalog, ["alpha"], [])

    def test_network_fetch_streams_and_second_sync_downloads_nothing(self):
        catalog = fixture()
        data = b"a" * (dist.CHUNK * 2 + 17)
        catalog["packages"]["alpha"]["files"]["alpha.bin"] = pin(data, ["https://example.invalid/alpha"])
        lock = dist.plan(catalog, ["alpha"], [])
        reads = []

        class Response(io.BytesIO):
            def read(self, n=-1):
                reads.append(n)
                if n < 0 or n > dist.CHUNK:
                    raise AssertionError("Unbounded download")
                return super().read(n)

        def open_url(url, **kwargs):
            return Response(data if url.endswith("alpha") else b"trees")

        with tempfile.TemporaryDirectory() as folder, patch.object(dist.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = open_url
            root = Path(folder)
            first = dist.sync(root, lock)
            self.assertEqual(first["download_bytes"], len(data) + 5)
            self.assertEqual(opener.return_value.open.call_count, 2)
            second = dist.sync(root, lock, offline=True)
            self.assertEqual(second["download_bytes"], 0)
            self.assertEqual(second["local_copy_bytes"], 0)
            self.assertEqual(opener.return_value.open.call_count, 2)
            self.assertTrue(dist.verify(root, lock)["ok"])
            self.assertTrue(reads)

    def test_unavailable_package_preflights_before_network_or_workspace_writes(self):
        catalog = fixture()
        catalog["packages"]["trees"]["availability"] = "local-only"
        lock = dist.plan(catalog, ["alpha"], [])
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.urllib.request, "build_opener") as opener:
            root = Path(folder) / "workspace"
            with self.assertRaisesRegex(ValueError, "no downloads started"):
                dist.sync(root, lock)
            opener.assert_not_called()
            self.assertFalse(root.exists())

    def test_explicit_local_files_work_offline_and_keep_originals(self):
        catalog = fixture()
        lock = dist.plan(catalog, ["alpha"], [])
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.urllib.request, "build_opener") as opener:
            root = Path(folder)
            write_sources(root / "source", catalog)
            result = dist.sync(root / "work", lock, [root / "source"], offline=True)
            self.assertEqual(result["download_bytes"], 0)
            self.assertEqual(result["local_copy_bytes"], 10)
            self.assertEqual(set(result["packages"]), {"alpha", "trees"})
            self.assertEqual((root / "source/alpha/alpha.bin").read_bytes(), b"alpha")
            opener.assert_not_called()

    def test_one_blob_is_fetched_once_even_when_multiple_packages_reference_it(self):
        catalog = fixture()
        catalog["packages"]["alpha"]["files"]["alpha.bin"] = copy.deepcopy(catalog["packages"]["trees"]["files"]["trees.bin"])
        lock = dist.plan(catalog, ["alpha"], [])
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(b"trees")
            result = dist.sync(Path(folder), lock)
            self.assertEqual(result["download_bytes"], 5)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_bad_and_interrupted_downloads_never_install_partial_bytes(self):
        lock = dist.plan(fixture(), [], ["trees"])
        for data in (b"wrong", b"trees-long", b"tre"):
            with self.subTest(data=data), tempfile.TemporaryDirectory() as folder, \
                    patch.object(dist.urllib.request, "build_opener") as opener:
                root = Path(folder)
                opener.return_value.open.return_value = io.BytesIO(data)
                with self.assertRaises(ValueError):
                    dist.sync(root, lock)
                self.assertFalse(list(root.rglob("*.part")))
                self.assertFalse((root / "distribution/packages").exists())
                self.assertFalse((root / "distribution/locks").exists())
                expected = lock["packages"]["trees"]["files"]["trees.bin"]
                self.assertFalse(dist.blob_path(root, expected).exists())
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.urllib.request, "build_opener") as opener:
            opener.return_value.open.side_effect = OSError("connection interrupted")
            with self.assertRaisesRegex(ValueError, "connection interrupted"):
                dist.sync(Path(folder), lock)
            self.assertFalse(list(Path(folder).rglob("*.part")))

    def test_corrupt_cache_and_installed_content_stop_without_overwriting(self):
        catalog = fixture()
        lock = dist.plan(catalog, [], ["trees"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_sources(root / "source", catalog)
            result = dist.sync(root / "work", lock, [root / "source"], offline=True)
            installed = Path(result["packages"]["trees"]) / "trees.bin"
            installed.write_bytes(b"edited")
            with self.assertRaisesRegex(ValueError, "Pinned file mismatch"):
                dist.sync(root / "work", lock, offline=True)
            self.assertEqual(installed.read_bytes(), b"edited")
            cache = dist.blob_path(root / "work", lock["packages"]["trees"]["files"]["trees.bin"])
            cache.write_bytes(b"bad")
            with self.assertRaisesRegex(ValueError, "Pinned file mismatch"), \
                    patch.object(dist.urllib.request, "build_opener") as opener:
                dist.sync(root / "work", lock)
            opener.assert_not_called()
            self.assertEqual(cache.read_bytes(), b"bad")

    def test_storage_migration_preserves_lock_and_can_supply_url_for_old_local_lock(self):
        catalog = fixture()
        catalog["packages"]["trees"]["files"]["trees.bin"]["urls"] = []
        catalog["packages"]["trees"]["availability"] = "local-only"
        lock = dist.plan(catalog, [], ["trees"])
        published = copy.deepcopy(catalog)
        published["packages"]["trees"]["files"]["trees.bin"]["urls"] = ["https://new-storage.invalid/trees"]
        published["packages"]["trees"]["availability"] = "public"
        self.assertEqual(dist.lock_id(lock), dist.lock_id(dist.plan(published, [], ["trees"])))
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.urllib.request, "build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(b"trees")
            self.assertTrue(dist.sync(Path(folder), lock, current=published)["ok"])
            opener.return_value.open.assert_called_once_with("https://new-storage.invalid/trees", timeout=60)
        published["packages"]["trees"]["files"]["trees.bin"] = pin(b"new model", ["https://new-storage.invalid/trees"])
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "unavailable"):
                dist.sync(Path(folder), lock, current=published)

    def test_new_version_coexists_and_old_lock_remains_usable(self):
        catalog = fixture()
        old = dist.plan(catalog, [], ["trees"])
        newer = copy.deepcopy(catalog)
        newer["packages"]["trees"]["version"] = "1.1.0"
        newer["packages"]["trees"]["files"]["trees.bin"] = pin(b"trees v2", [])
        new = dist.plan(newer, [], ["trees"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_sources(root / "source", catalog)
            first = dist.sync(root / "work", old, [root / "source"], offline=True)
            (root / "source/trees/trees.bin").write_bytes(b"trees v2")
            second = dist.sync(root / "work", new, [root / "source"], offline=True)
            self.assertNotEqual(first["packages"]["trees"], second["packages"]["trees"])
            self.assertTrue(dist.verify(root / "work", old)["ok"])
            self.assertTrue(dist.verify(root / "work", new)["ok"])
            self.assertEqual(dist.sync(root / "work", old, offline=True)["download_bytes"], 0)

    def test_modified_saved_lock_is_not_returned_as_the_requested_configuration(self):
        catalog = fixture()
        lock = dist.plan(catalog, [], ["trees"])
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            write_sources(root / "source", catalog)
            result = dist.sync(root / "work", lock, [root / "source"], offline=True)
            changed = copy.deepcopy(lock)
            changed["packages"]["trees"]["version"] = "9.0.0"
            dist.ws.write_json(result["lock"], changed)
            with self.assertRaisesRegex(ValueError, "Saved lock differs"):
                dist.sync(root / "work", lock, offline=True)
            self.assertEqual(dist.ws.read_json(result["lock"])["packages"]["trees"]["version"], "9.0.0")

    def archive_fixture(self, folder, extra=None):
        files = {"kit.blend": b"synthetic mesh", "NOTICE.md": b"fixture attribution"}
        archive = folder / "kit.zip"
        with zipfile.ZipFile(archive, "w") as zipped:
            for name, data in files.items():
                zipped.writestr(name, data)
            if extra:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", UserWarning)
                    zipped.writestr(extra, b"unexpected")
        catalog = fixture()
        catalog["packages"]["trees"].update({"files": {"kit.zip": pin(archive.read_bytes(), [])}, "archive": "kit.zip",
                                               "members": {n: pin(v) for n, v in files.items()},
                                               "scene": "kit.blend", "expected_meshes": 1})
        return dist.plan(catalog, [], ["trees"])

    def test_archive_roundtrip_and_member_hash_verification(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            lock = self.archive_fixture(root)
            result = dist.sync(root / "work", lock, [root], offline=True)
            package = Path(result["packages"]["trees"])
            self.assertEqual((package / "NOTICE.md").read_bytes(), b"fixture attribution")
            self.assertEqual(Path(result["scenes"]["trees"]).read_bytes(), b"synthetic mesh")
            self.assertTrue(dist.verify(root / "work", lock)["ok"])
            broken = copy.deepcopy(lock)
            broken["packages"]["trees"]["members"]["kit.blend"] = pin(b"wrong")
            with self.assertRaises(ValueError):
                dist.sync(root / "work", broken, [root], offline=True)
            self.assertFalse(dist.package_path(root / "work", "trees", broken["packages"]["trees"]).exists())

    def test_duplicate_traversal_and_extra_archive_members_are_rejected(self):
        for extra in ("kit.blend", "../outside", "unapproved-city.blend"):
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                lock = self.archive_fixture(root, extra)
                with self.assertRaisesRegex(ValueError, "Archive members"):
                    dist.sync(root / "work", lock, [root], offline=True)
                self.assertFalse((root / "outside").exists())
                self.assertFalse((root / "work/distribution/locks").exists())

    def test_nonportable_paths_and_http_urls_are_rejected_before_io(self):
        for bad in ("../x", "x/../y", "/abs", "C:/x", "dir\\x", "CON", "a/", "a.", "x:y"):
            catalog = fixture()
            catalog["packages"]["trees"]["files"] = {bad: pin(b"x")}
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                dist.plan(catalog, [], ["trees"])
        for bad in ("http://example.invalid/a", "file:///a", "https://user:pass@example.invalid/a"):
            catalog = fixture()
            catalog["packages"]["trees"]["files"]["trees.bin"]["urls"] = [bad]
            with self.subTest(bad=bad), self.assertRaisesRegex(ValueError, "HTTPS"):
                dist.plan(catalog, [], ["trees"])
        with self.assertRaisesRegex(ValueError, "non-HTTPS"):
            dist.ws.HTTPSRedirects().redirect_request(None, None, 302, "", {}, "http://example.invalid")

    def test_old_lock_stops_changed_recipe_before_blender_or_download(self):
        lock = dist.plan(fixture(), [], ["trees"])
        lock["code_sha256_lf"]["scripts/workspace.py"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.ws, "blender_check") as blender, \
                patch.object(dist, "sync") as fetch:
            with self.assertRaisesRegex(ValueError, "Code differs"):
                dist.setup(Path(folder), lock, Path("blender"))
            blender.assert_not_called()
            fetch.assert_not_called()

    def test_checked_in_catalog_matches_existing_input_and_approved_package_records(self):
        catalog = dist.validate_catalog(dist.ws.read_json(dist.CATALOG))
        workspace = dist.ws.load_catalog()
        for name, spec in catalog["packages"]["plateau-minato-tile221"]["files"].items():
            reference = workspace["sources"]["plateau-minato-2025"]["files"][name]
            self.assertEqual({k: spec[k] for k in ("bytes", "sha256")}, {k: reference[k] for k in ("bytes", "sha256")})
            self.assertEqual(spec["urls"], [reference["url"]])
        record = dist.ws.read_json(ROOT / "assets/procedural-components/package-v0.1.0.json")
        package = catalog["packages"]["procedural-components"]
        self.assertEqual(package["files"][package["archive"]]["sha256"], record["package"]["sha256"])
        self.assertEqual(set(package["members"]), set(record["archive_members"]))
        for name, expected in record["inventory"]["files"].items():
            self.assertEqual(package["members"][name], expected)
        self.assertEqual(package["availability"], "local-only")
        self.assertFalse(package["files"][package["archive"]]["urls"])
        self.assertEqual(catalog["districts"]["mori"]["scope"]["expected_meshes"], 42)
        self.assertIsNone(catalog["districts"]["mori"]["scope"]["geographic_boundary"])

    def test_cli_dispatch_and_lock_file_cannot_be_silently_overwritten(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()) as output:
            root = Path(folder)
            args = ["district", "plan", "--district", "mori", "--workspace", str(root / "workspace"),
                    "--output", str(root / "lock.json")]
            self.assertEqual(dist.ws.main(args), 0)
            self.assertEqual(json.loads(output.getvalue())["download_bytes"], 1658929)
            original = (root / "lock.json").read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(dist.ws.main(args), 1)
            self.assertEqual((root / "lock.json").read_bytes(), original)
            self.assertFalse((root / "workspace").exists())

    def test_prebuilt_district_setup_reuses_files_and_edit_keeps_nested_paths_and_notices(self):
        catalog = fixture()
        package = catalog["packages"]["alpha"]
        package["files"] = {"scenes/main.blend": pin(b"fixture scene", []), "NOTICE.md": pin(b"credit", [])}
        package.update({"scene": "scenes/main.blend", "expected_meshes": 1})
        lock = dist.plan(catalog, ["alpha"], [])
        check = {"scene": {"self_contained_images_libraries": True}}
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.ws, "blender_check", return_value=check):
            root = Path(folder)
            write_sources(root / "source", fixture())
            (root / "source/alpha/scenes").mkdir()
            (root / "source/alpha/scenes/main.blend").write_bytes(b"fixture scene")
            (root / "source/alpha/NOTICE.md").write_bytes(b"credit")
            first = dist.setup(root / "work", lock, Path("blender"), [root / "source"], offline=True)
            self.assertFalse(first["districts"]["alpha"]["reused"])
            self.assertIn("--workspace '" + str(root / "work") + "'", first["districts"]["alpha"]["edit_command"])
            second = dist.setup(root / "work", lock, Path("blender"), offline=True)
            self.assertTrue(second["districts"]["alpha"]["reused"])
            edited = dist.edit(root / "work", lock)
            destination = Path(edited["editable_copy"])
            self.assertEqual(destination.read_bytes(), b"fixture scene")
            self.assertEqual((destination.parents[1] / "NOTICE.md").read_bytes(), b"credit")
            destination.write_bytes(b"edited by contributor")
            self.assertEqual(Path(first["districts"]["alpha"]["scene"]).read_bytes(), b"fixture scene")
            self.assertTrue(dist.verify(root / "work", lock)["ok"])

    def test_failed_prebuilt_scene_check_does_not_register_ready_build(self):
        catalog = fixture()
        package = catalog["packages"]["alpha"]
        package.update({"scene": "alpha.bin", "expected_meshes": 1})
        lock = dist.plan(catalog, ["alpha"], [])
        with tempfile.TemporaryDirectory() as folder, patch.object(dist.ws, "blender_check") as check:
            root = Path(folder)
            write_sources(root / "source", catalog)
            check.return_value = {"scene": {"self_contained_images_libraries": False}}
            with self.assertRaisesRegex(ValueError, "pack images"):
                dist.setup(root / "work", lock, Path("blender"), [root / "source"], offline=True)
            self.assertFalse(dist.receipt_path(root / "work", lock, "alpha").exists())

    def test_mori_adapter_uses_pinned_inputs_and_does_not_rebuild_for_added_shared_library(self):
        catalog = dist.ws.read_json(dist.CATALOG)
        original = dist.plan(catalog, ["mori"], [])
        with_shared = dist.plan(catalog, ["mori"], ["procedural-components"])
        self.assertEqual(dist.build_identity(original, "mori"), dist.build_identity(with_shared, "mori"))
        checked = {"scene": {"self_contained_images_libraries": True}}
        with tempfile.TemporaryDirectory() as folder, patch.object(dist, "sync") as sync, \
                patch.object(dist.ws, "blender_check", return_value=checked), patch.object(dist.ws, "setup_mori") as build:
            root = Path(folder)
            sync.side_effect = lambda work, lock, *a: {"lock": str(work / "lock.json")}

            def generate(work, blender, workspace_catalog, inputs):
                self.assertEqual(inputs, dist.package_path(work, "plateau-minato-tile221", original["packages"]["plateau-minato-tile221"]))
                scene = work / "builds/fixture/after.blend"
                scene.parent.mkdir(parents=True)
                scene.write_bytes(b"scene")
                return {"scene": "builds/fixture/after.blend", "files": {"builds/fixture/after.blend": pin(b"scene")}}

            build.side_effect = generate
            first = dist.setup(root, original, Path("blender"))
            self.assertFalse(first["districts"]["mori"]["reused"])
            # Supply the already verified common scene for the independent library check.
            library = dist.package_path(root, "procedural-components", with_shared["packages"]["procedural-components"]) / "kit.blend"
            library.parent.mkdir(parents=True)
            library.write_bytes(b"fixture")
            with patch.object(dist.ws, "verify_file", wraps=dist.ws.verify_file) as verify:
                def verify_known(path, spec):
                    return path if path == library else real_verify(path, spec)
                real_verify = verify._mock_wraps
                verify.side_effect = verify_known
                second = dist.setup(root, with_shared, Path("blender"))
            self.assertTrue(second["districts"]["mori"]["reused"])
            self.assertEqual(build.call_count, 1)

    def test_changed_mori_input_cannot_be_passed_to_existing_adapter(self):
        lock = dist.plan(dist.ws.read_json(dist.CATALOG), ["mori"], [])
        lock["packages"]["plateau-minato-tile221"]["files"]["data221.b3dm"]["sha256"] = "0" * 64
        with tempfile.TemporaryDirectory() as folder, patch.object(dist, "sync") as sync:
            with self.assertRaisesRegex(ValueError, "adapter inputs differ"):
                dist.setup(Path(folder), lock, Path("blender"))
            sync.assert_not_called()


if __name__ == "__main__":
    unittest.main()

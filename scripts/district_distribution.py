# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Select districts and shared packages, lock their versions, and fetch only those bytes."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid
import zipfile

import workspace as ws

ROOT = ws.ROOT
CATALOG = ROOT / "manifests/district-distribution.json"
CHUNK = 1024 * 1024


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode("utf8")).hexdigest()


def portable_path(value):
    require(isinstance(value, str) and bool(value), "Missing relative file name")
    # Use the same names on Windows/macOS/Linux, including case-insensitive filesystems.
    for part in value.split("/"):
        require(part not in {"", ".", ".."} and not re.search(r'[\\<>:"|?*\x00-\x1f]', part)
                and not part.endswith((".", " ")) and
                not re.fullmatch(r"(?i:con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\..*)?", part),
                "Non-portable relative file name: " + value)
    return value


def check_files(files):
    require(isinstance(files, dict) and bool(files), "Package has no files")
    names = set()
    for name, pin in files.items():
        portable_path(name)
        lower = name.casefold()
        require(lower not in names, "Case-insensitive duplicate file")
        names.add(lower)
        require(type(pin.get("bytes")) is int and pin["bytes"] >= 0, "Invalid byte count")
        require(isinstance(pin.get("sha256"), str) and re.fullmatch("[0-9a-f]{64}", pin["sha256"]),
                "Invalid SHA-256")
        require(isinstance(pin.get("urls", []), list), "URLs must be a list")
        for url in pin.get("urls", []):
            parsed = urllib.parse.urlsplit(url)
            require(parsed.scheme == "https" and parsed.hostname and not parsed.username and not parsed.password,
                    "Package URLs must use HTTPS without credentials")
    for name in names:
        require(not any(name.startswith(other + "/") for other in names), "File/directory collision")


def validate_catalog(catalog):
    require(catalog.get("schema_version") == 1, "Unsupported district catalog")
    require(catalog["runtime"] == {"blender_version": "4.5.1", "runner_python_versions": [[3, 11], [3, 12]]},
            "Unsupported district runtime")
    packages = catalog["packages"]
    require(isinstance(packages, dict), "Missing packages")
    for key, package in packages.items():
        require(re.fullmatch("[a-z0-9]+(?:-[a-z0-9]+)*", key), "Invalid package ID")
        require(re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:-[a-z0-9.-]+)?", package["version"]),
                "Use an exact package version")
        require(package["kind"] in {"source", "shared"}, "Unknown package kind")
        require(package.get("notice") and package.get("license"), "Missing source/license notice")
        require(package.get("availability") in {"public", "local-only"}, "Unknown availability")
        require(isinstance(package["requires"], list) and len(set(package["requires"])) == len(package["requires"]),
                "Invalid dependencies")
        require(all(item in packages for item in package["requires"]), "Unknown package dependency")
        check_files(package["files"])
        if "archive" in package:
            require(package["archive"] in package["files"] and len(package["files"]) == 1,
                    "An archive package must have exactly one ZIP")
            check_files(package["members"])
        else:
            require("members" not in package, "Members require an archive")
        members = package.get("members", package["files"])
        if package.get("scene"):
            require(package["scene"] in members and type(package.get("expected_meshes")) is int,
                    "Scene must be pinned in the package")
    for key, district in catalog["districts"].items():
        require(re.fullmatch("[a-z0-9]+(?:-[a-z0-9]+)*", key), "Invalid district ID")
        require(district.get("packages") and all(p in packages for p in district["packages"]),
                "Unknown district package")
        require(district.get("scope") and district.get("frame"), "Missing district scope/frame")
        require(district.get("adapter") in {"mori-v1", "blend-package-v1"}, "Unknown build adapter")
        require(district.get("input_package") in district["packages"], "Missing district input package")
        require(isinstance(district.get("recipe_files"), list), "Missing recipe file list")
    return catalog


def closure(packages, roots):
    visiting, done, ordered = set(), set(), []

    def visit(key):
        require(key in packages, "Unknown package: " + key)
        require(key not in visiting, "Package dependency cycle: " + key)
        if key in done:
            return
        visiting.add(key)
        for child in sorted(packages[key]["requires"]):
            visit(child)
        visiting.remove(key)
        done.add(key)
        ordered.append(key)

    for key in sorted(set(roots)):
        visit(key)
    return ordered


def content(value):
    """Storage URLs can move without changing content identity or cached paths."""
    if isinstance(value, dict):
        return {key: content(item) for key, item in value.items() if key not in {"urls", "availability"}}
    if isinstance(value, list):
        return [content(item) for item in value]
    return value


def package_id(package):
    return digest_json(content(package))


def lock_id(lock):
    return digest_json(content(lock))


def code_hash(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def check_mori_contract(district, runtime, catalog):
    # Pin the settings used by the adapter, not unrelated distribution URLs in
    # contributor-workspace.json. Moving a download must not invalidate a build.
    profile = catalog["profiles"]["mori"]
    expected = {key: profile[key] for key in ("runner", "scene", "expected_meshes", "distribution")}
    expected["source_notice"] = catalog["sources"]["plateau-minato-2025"]["notice"]
    require(district.get("adapter_contract") == expected and runtime == {
        key: catalog[key] for key in ("blender_version", "runner_python_versions")},
        "Mori adapter configuration differs from lock/catalog; review the recipe version")


def plan(catalog, districts, common, root=ROOT):
    validate_catalog(catalog)
    require(districts or common, "Select --district and/or --common; use district list to see choices")
    require(all(key in catalog["districts"] for key in districts), "Unknown district; no fallback is used")
    require(all(key in catalog["packages"] and catalog["packages"][key]["kind"] == "shared" for key in common),
            "Unknown shared package")
    selected = {key: copy.deepcopy(catalog["districts"][key]) for key in sorted(set(districts))}
    roots = list(common) + [p for district in selected.values() for p in district["packages"]]
    packages = {key: copy.deepcopy(catalog["packages"][key]) for key in closure(catalog["packages"], roots)}
    paths = set(catalog["tool_files"])
    for district in selected.values():
        if district["adapter"] == "mori-v1":
            check_mori_contract(district, catalog["runtime"], ws.load_catalog())
        paths.update(district["recipe_files"])
    code = {name: code_hash(ws.inside(root, portable_path(name))) for name in sorted(paths)}
    return {"schema_version": 1, "runtime": copy.deepcopy(catalog["runtime"]), "districts": selected,
            "common": sorted(set(common)), "packages": packages, "code_sha256_lf": code}


def validate_lock(lock):
    validate_catalog(lock)
    require(isinstance(lock.get("code_sha256_lf"), dict) and lock["code_sha256_lf"], "Missing code lock")
    for name, sha in lock["code_sha256_lf"].items():
        portable_path(name)
        require(isinstance(sha, str) and re.fullmatch("[0-9a-f]{64}", sha), "Invalid code hash")
    roots = lock["common"] + [p for d in lock["districts"].values() for p in d["packages"]]
    require(roots and set(closure(lock["packages"], roots)) == set(lock["packages"]), "Unexpected locked packages")
    require(all(lock["packages"][key]["kind"] == "shared" for key in lock["common"]), "Invalid common selection")
    return lock


def blob_path(workspace, pin):
    return ws.inside(workspace, "distribution/blobs/sha256/" + pin["sha256"])


def package_path(workspace, key, package):
    return ws.inside(workspace, f"distribution/packages/{key}/{package['version']}-{package_id(package)}")


def explicit_source(directories, key, name, pin):
    for directory in directories:
        for relative in (key + "/" + name, name):
            source = ws.inside(directory, relative)
            if source.exists():
                return ws.verify_file(source, pin)
    return None


def locations(package, name, pin, key, current):
    urls = list(pin.get("urls", [])) if package["availability"] == "public" else []
    # A newly registered mirror is usable only for the exact same package content.
    newer = current.get("packages", {}).get(key, {}) if current else {}
    if newer and newer.get("availability") == "public" and package_id(newer) == package_id(package):
        urls += newer["files"][name].get("urls", [])
    return list(dict.fromkeys(urls))


def inspect(workspace, lock, directories=(), offline=False, current=None):
    validate_lock(lock)
    blobs, entries = {}, []
    for key, package in lock["packages"].items():
        for name, pin in package["files"].items():
            sha = pin["sha256"]
            target = blob_path(workspace, pin)
            source = explicit_source(directories, key, name, pin)
            urls = locations(package, name, pin, key, current)
            if target.exists():
                ws.verify_file(target, pin)
                state = "cached"
            elif source:
                state = "local"
            elif urls and not offline:
                state = "download"
            else:
                state = "unavailable"
            entry = {"package": key, "version": package["version"], "file": name, "bytes": pin["bytes"],
                     "sha256": sha, "state": state}
            entries.append(entry)
            if sha in blobs:
                require(blobs[sha]["bytes"] == pin["bytes"], "One hash has conflicting byte counts")
            priority = {"cached": 0, "local": 1, "download": 2, "unavailable": 3}
            if sha not in blobs or priority[state] < priority[blobs[sha]["state"]]:
                blobs[sha] = {**entry, "source": source, "urls": urls, "target": target}
            else:
                blobs[sha]["urls"] = list(dict.fromkeys(blobs[sha]["urls"] + urls))
    return {"lock_id": lock_id(lock), "files": entries,
            "unique_bytes": sum(x["bytes"] for x in blobs.values()),
            "download_bytes": sum(x["bytes"] for x in blobs.values() if x["state"] == "download"),
            "local_copy_bytes": sum(x["bytes"] for x in blobs.values() if x["state"] == "local"),
            "unavailable": [x["file"] for x in blobs.values() if x["state"] == "unavailable"],
            "scope": {key: d["scope"] for key, d in lock["districts"].items()}}, blobs


def stream_checked(reader, writer, pin):
    digest, size = hashlib.sha256(), 0
    while True:
        block = reader.read(min(CHUNK, pin["bytes"] - size + 1))
        if not block:
            break
        size += len(block)
        require(size <= pin["bytes"], "Downloaded/extracted file exceeds pinned size")
        digest.update(block)
        writer.write(block)
    require(size == pin["bytes"] and digest.hexdigest() == pin["sha256"], "Pinned bytes/hash mismatch")


def acquire(entry):
    target = entry["target"]
    if target.exists():
        return ws.verify_file(target, entry)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".part")
    try:
        if entry["source"]:
            with entry["source"].open("rb") as reader, temporary.open("xb") as writer:
                stream_checked(reader, writer, entry)
        else:
            errors = []
            for url in entry["urls"]:
                try:
                    opener = urllib.request.build_opener(ws.HTTPSRedirects())
                    with opener.open(url, timeout=60) as reader, temporary.open("wb") as writer:
                        stream_checked(reader, writer, entry)
                    break
                except (OSError, ValueError) as error:
                    errors.append(str(error))
            else:
                raise ValueError("All locations failed for " + entry["file"] + ": " + "; ".join(errors))
        # Only fully verified bytes enter the persistent cache. Partial files are discarded.
        if target.exists():
            ws.verify_file(target, entry)
        else:
            os.replace(temporary, target)
        return target
    finally:
        temporary.unlink(missing_ok=True)


def check_installed(folder, files):
    require(folder.is_dir(), "Package is not installed: " + str(folder))
    def unreadable(error):
        raise error
    actual = set()
    for parent, directories, names in os.walk(folder, onerror=unreadable, followlinks=False):
        require(not any((Path(parent) / name).is_symlink() for name in directories), "Linked package directory")
        actual.update((Path(parent) / name).relative_to(folder).as_posix() for name in names)
    require(actual == set(files), "Installed package file set differs from lock: " + str(folder))
    for name, pin in files.items():
        ws.verify_file(ws.inside(folder, name), pin)
    return folder


def install_package(workspace, key, package):
    target = package_path(workspace, key, package)
    files = package.get("members", package["files"])
    if target.exists():
        return check_installed(target, files)
    target.parent.mkdir(parents=True, exist_ok=True)
    # mkdir inherits the workspace ACL. TemporaryDirectory's private Windows ACL
    # would otherwise follow a renamed payload into the permanent package cache.
    staging = target.parent / (".install-" + uuid.uuid4().hex)
    staging.mkdir()
    try:
        payload = staging / "payload"
        payload.mkdir()
        if "archive" in package:
            archive = blob_path(workspace, package["files"][package["archive"]])
            with zipfile.ZipFile(archive) as zipped:
                info = zipped.infolist()
                require(len(info) == len(files) and {i.filename for i in info} == set(files),
                        "Archive members differ from lock")
                for item in info:
                    pin = files[item.filename]
                    require(not item.is_dir() and not stat.S_ISLNK(item.external_attr >> 16)
                            and item.file_size == pin["bytes"], "Unexpected archive member")
                    destination = ws.inside(payload, item.filename)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zipped.open(item) as reader, destination.open("xb") as writer:
                        stream_checked(reader, writer, pin)
        else:
            for name, pin in files.items():
                ws.copy_verified(blob_path(workspace, pin), ws.inside(payload, name), pin)
        check_installed(payload, files)
        if target.exists():
            check_installed(target, files)
        else:
            payload.rename(target)
    finally:
        require(staging.resolve().is_relative_to(Path(workspace).resolve()), "Staging cleanup escaped workspace")
        shutil.rmtree(staging)
    return target


def sync(workspace, lock, directories=(), offline=False, current=None):
    report, blobs = inspect(workspace, lock, directories, offline, current)
    require(not report["unavailable"], "Packages unavailable; no downloads started: " + ", ".join(report["unavailable"])
            + ". Supply --source-dir PATH or wait for a published URL; use --offline only with local inputs/cache.")
    for entry in blobs.values():
        acquire(entry)
    paths = {key: install_package(workspace, key, p) for key, p in lock["packages"].items()}
    saved = ws.inside(workspace, "distribution/locks/" + lock_id(lock) + ".json")
    if saved.exists():
        require(lock_id(validate_lock(ws.read_json(saved))) == lock_id(lock),
                "Saved lock differs from its content ID; existing records are not overwritten")
    else:
        ws.write_json(saved, lock)
    return {**report, "ok": True, "lock": str(saved), "packages": {k: str(p) for k, p in paths.items()},
            "scenes": {key: str(paths[key] / p["scene"]) for key, p in lock["packages"].items() if p.get("scene")}}


def verify(workspace, lock):
    validate_lock(lock)
    for key, package in lock["packages"].items():
        for pin in package["files"].values():
            ws.verify_file(blob_path(workspace, pin), pin)
        check_installed(package_path(workspace, key, package), package.get("members", package["files"]))
    return {"ok": True, "lock_id": lock_id(lock), "verified_packages": sorted(lock["packages"]),
            "validation": "Pinned files and archive contents; not a Blender/real-world accuracy check"}


def check_code(lock, root=ROOT):
    for name, expected in lock["code_sha256_lf"].items():
        require(code_hash(ws.inside(root, name)) == expected,
                "Code differs from the shared lock: " + name + ". Check out the matching code version.")


def build_identity(lock, key):
    district = lock["districts"][key]
    relevant = closure(lock["packages"], district["packages"])
    # Other selected districts and optional libraries do not invalidate this district's build.
    used_code = set(district["recipe_files"]) | {"scripts/district_distribution.py", "scripts/workspace.py",
                                               "scripts/workspace_blender.py"}
    return digest_json(content({"district": district, "runtime": lock["runtime"],
                               "packages": {p: lock["packages"][p] for p in relevant},
                               "code_sha256_lf": {p: lock["code_sha256_lf"][p] for p in sorted(used_code)}}))


def receipt_path(workspace, lock, key):
    return ws.inside(workspace, "distribution/builds/" + key + "/" + build_identity(lock, key) + ".json")


def read_build(workspace, lock, key):
    path = receipt_path(workspace, lock, key)
    require(path.is_file(), "District is not built for this lock; run district setup first: " + key)
    record = ws.read_json(path)
    require(record["district_build_id"] == build_identity(lock, key), "Build identity differs from lock")
    for relative, expected in record["files"].items():
        ws.verify_file(ws.inside(workspace, relative), expected)
    require(record["scene"] in record["files"], "Build scene is not recorded")
    return record


def check_self_contained(check):
    require(check["scene"].get("self_contained_images_libraries") is True,
            "Distributed scenes must pack images and have no linked libraries")


def setup(workspace, lock, blender, directories=(), offline=False, current=None):
    validate_lock(lock)
    check_code(lock)
    catalog = ws.load_catalog()
    # This adapter is intentionally explicit. Catalogs and locks cannot execute commands.
    for key, district in lock["districts"].items():
        package = lock["packages"][district["input_package"]]
        if district["adapter"] == "mori-v1":
            require(key == "mori", "Mori adapter is specific to the Mori district")
            check_mori_contract(district, lock["runtime"], catalog)
            reference = catalog["sources"]["plateau-minato-2025"]["files"]
            require(set(package["files"]) == set(reference) and all(
                all(package["files"][name][field] == reference[name][field] for field in ("bytes", "sha256"))
                for name in reference), "Mori adapter inputs differ from the locked official tile")
        else:
            require(package.get("scene"), "Prebuilt district package has no scene")
    ws.blender_check(workspace, blender, lock["runtime"])
    result = sync(workspace, lock, directories, offline, current)
    built = {}
    for key, district in lock["districts"].items():
        build_id = build_identity(lock, key)
        receipt = receipt_path(workspace, lock, key)
        package = lock["packages"][district["input_package"]]
        expected_meshes = (catalog["profiles"][key]["expected_meshes"] if district["adapter"] == "mori-v1"
                           else package["expected_meshes"])
        if receipt.exists():
            record = read_build(workspace, lock, key)
            reused = True
        else:
            inputs = package_path(workspace, district["input_package"], package)
            if district["adapter"] == "mori-v1":
                record = ws.setup_mori(workspace, blender, catalog, inputs)
                record["content_root"] = str(Path(record["scene"]).parent.as_posix())
            else:
                files = package.get("members", package["files"])
                record = {"scene": (inputs / package["scene"]).relative_to(workspace).as_posix(),
                          "content_root": inputs.relative_to(workspace).as_posix(),
                          "files": {(inputs / n).relative_to(workspace).as_posix(): p for n, p in files.items()}}
            record["district_build_id"] = build_id
            reused = False
        check = ws.blender_check(workspace, blender, lock["runtime"], ws.inside(workspace, record["scene"]), expected_meshes)
        check_self_contained(check)
        # Recheck after Blender and only then record the build as ready for this lock.
        for relative, expected in record["files"].items():
            ws.verify_file(ws.inside(workspace, relative), expected)
        record["distribution_lock"] = "distribution/locks/" + lock_id(lock) + ".json"
        ws.write_json(receipt, record)
        if key == "mori":
            ws.save_profile(workspace, key, record)
        built[key] = {"scene": str(ws.inside(workspace, record["scene"])), "reused": reused,
                      "edit_command": ".\\otw.ps1 district edit --lock '" + result["lock"].replace("'", "''")
                      + "' --workspace '" + str(workspace).replace("'", "''") + "' --open"}
    checks = {}
    for key, package in lock["packages"].items():
        if package.get("scene"):
            scene = package_path(workspace, key, package) / package["scene"]
            checks[key] = ws.blender_check(workspace, blender, lock["runtime"], scene, package["expected_meshes"])
            check_self_contained(checks[key])
            ws.verify_file(scene, package.get("members", package["files"])[package["scene"]])
    return {**result, "districts": built, "shared_scene_checks": checks,
            "assembly_note": "Districts open separately. Shared libraries are available for append; no automatic placement or city merge."}


def edit(workspace, lock, blender=None):
    check_code(lock)
    verify(workspace, lock)
    require(len(lock["districts"]) == 1, "Select exactly one district to edit")
    key, district = next(iter(lock["districts"].items()))
    record = read_build(workspace, lock, key)
    if blender:
        ws.blender_check(workspace, blender, lock["runtime"])
    output = ws.unique_folder(workspace, "edits", key)
    output.mkdir()
    base = ws.inside(workspace, record["content_root"])
    payload = output / "files"
    for relative, pin in record["files"].items():
        source = ws.inside(workspace, relative)
        # Preserve package subfolders and attribution; do not copy unrelated workspace files.
        name = source.relative_to(base).as_posix()
        ws.copy_verified(source, ws.inside(payload, name), pin)
    destination = ws.inside(payload, ws.inside(workspace, record["scene"]).relative_to(base).as_posix())
    ws.write_json(output / "edit.json", {"district": key, "scene": destination.relative_to(output).as_posix(),
                  "reference_sha256": record["files"][record["scene"]]["sha256"],
                  "distribution_lock": record["distribution_lock"], "district_build_id": record["district_build_id"],
                  "validated_edit": False})
    if blender:
        subprocess.Popen([str(blender), "--disable-autoexec", str(destination)])
    return {"editable_copy": str(destination), "opened": bool(blender), "validated_edit": False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["list", "plan", "sync", "verify", "setup", "edit"])
    parser.add_argument("--district", action="append", default=[], help="Select a district; repeat for several")
    parser.add_argument("--common", action="append", default=[], help="Add a shared package; repeat as needed")
    parser.add_argument("--lock", type=Path, help="Reuse an exact shared lock instead of making a new selection")
    parser.add_argument("--output", type=Path, help="Save a plan lock to a new file")
    parser.add_argument("--workspace", type=Path, default=ROOT / "data/local")
    parser.add_argument("--source-dir", type=Path, action="append", default=[], help="Explicit local files or package-ID subfolders")
    parser.add_argument("--offline", action="store_true", help="Use local sources/cache only; never use the network")
    parser.add_argument("--blender", type=Path)
    parser.add_argument("--open", action="store_true", help="Open the new district edit copy in Blender")
    args = parser.parse_args(argv)
    try:
        current = validate_catalog(ws.read_json(CATALOG))
        require(not args.output or args.action == "plan", "--output is for plan only")
        require(not args.open or args.action == "edit", "--open is for edit only")
        if args.action == "list":
            result = {"districts": {k: {"label": d["label"], "scope": d["scope"]} for k, d in current["districts"].items()},
                      "common": {k: {"version": p["version"], "availability": p["availability"], "notice": p["notice"]}
                                 for k, p in current["packages"].items() if p["kind"] == "shared"},
                      "full_city_distribution": "pending; not an alias for the Mori district"}
        else:
            require(not args.lock or not (args.district or args.common), "Use --lock or a new selection, not both")
            lock = validate_lock(ws.read_json(args.lock)) if args.lock else plan(current, args.district, args.common)
            root = args.workspace.resolve()
            directories = [p.resolve() for p in args.source_dir]
            if args.action == "plan":
                result, _ = inspect(root, lock, directories, args.offline, current)
                if args.output:
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    with args.output.open("x", encoding="utf8") as out:
                        json.dump(lock, out, ensure_ascii=False, indent=2, allow_nan=False)
                        out.write("\n")
                    result["saved_lock"] = str(args.output.resolve())
            elif args.action == "sync":
                result = sync(root, lock, directories, args.offline, current)
            elif args.action == "verify":
                result = verify(root, lock)
                result["built_districts"] = {}
                for key in lock["districts"]:
                    if receipt_path(root, lock, key).exists():
                        record = read_build(root, lock, key)
                        result["built_districts"][key] = record["scene"]
            elif args.action == "edit":
                result = edit(root, lock, ws.find_blender(args.blender) if args.open else None)
            else:
                result = setup(root, lock, ws.find_blender(args.blender), directories, args.offline, current)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, subprocess.SubprocessError) as error:
        print("District distribution error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

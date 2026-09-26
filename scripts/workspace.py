# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""One local workspace for contributor setup, pinned inputs and editable copies."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "manifests/contributor-workspace.json"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inside(root, relative):
    """Reject absolute paths, parent traversal and links escaping the workspace."""
    if not isinstance(relative, str) or not relative or "\\" in relative or ":" in relative:
        raise ValueError("Expected a workspace-relative path")
    value = Path(relative)
    root = Path(root).resolve()
    if value.is_absolute() or ".." in value.parts:
        raise ValueError("Path escapes workspace")
    result = (root / value).resolve()
    if result == root or not result.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    return result


def digest(path):
    result = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def verify_file(path, expected):
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Missing file: {path}")
    if path.stat().st_size != expected["bytes"] or digest(path) != expected["sha256"]:
        raise ValueError(f"Pinned file mismatch: {path}. Existing files are never silently replaced.")
    return path


def copy_verified(source, target, expected):
    """Verify both ends, never overwrite an existing file, preserve the source."""
    source, target = Path(source), Path(target)
    verify_file(source, expected)
    if target.exists():
        return verify_file(target, expected)
    target.parent.mkdir(parents=True, exist_ok=True)
    with source.open("rb") as reader, target.open("xb") as writer:
        shutil.copyfileobj(reader, writer, 8 * 1024 * 1024)
    return verify_file(target, expected)


class HTTPSRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlparse(newurl).scheme != "https":
            raise ValueError("Refusing a non-HTTPS redirect")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_file(target, specification):
    target = Path(target)
    if target.exists():
        return verify_file(target, specification)
    if urllib.parse.urlparse(specification["url"]).scheme != "https":
        raise ValueError("Source URL must use HTTPS")
    opener = urllib.request.build_opener(HTTPSRedirects())
    with opener.open(specification["url"], timeout=60) as response:
        data = response.read(specification["bytes"] + 1)
    if len(data) != specification["bytes"] or hashlib.sha256(data).hexdigest() != specification["sha256"]:
        raise ValueError("Downloaded source differs from pinned bytes/hash: " + target.name)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(data)
    return target


def load_catalog():
    catalog = read_json(CATALOG)
    if catalog.get("schema_version") != 1 or set(catalog["profiles"]) != {"city", "mori"}:
        raise ValueError("Unsupported contributor catalog")
    return catalog


def unique_folder(workspace, group, label):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = inside(workspace, f"{group}/{label}-{stamp}-{uuid.uuid4().hex[:8]}")
    # The existing generator itself creates and refuses to reuse this directory.
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def find_blender(explicit=None):
    candidates = [explicit, os.environ.get("OTW_BLENDER"), shutil.which("blender")]
    if sys.platform == "win32":
        candidates.append(Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Blender Foundation/Blender 4.5/blender.exe")
    elif sys.platform == "darwin":
        candidates.append(Path("/Applications/Blender.app/Contents/MacOS/Blender"))
    # An explicit bad path is an error, not permission to use a different Blender.
    if explicit or os.environ.get("OTW_BLENDER"):
        candidate = Path(explicit or os.environ["OTW_BLENDER"]).expanduser().resolve()
        if not candidate.is_file():
            raise ValueError("Blender executable missing: " + str(candidate))
        return candidate
    for value in candidates:
        if value and Path(value).is_file():
            return Path(value).resolve()
    raise ValueError("Blender 4.5.1 is required. Install/extract it and supply --blender PATH. See docs/contributor-workspace.md.")


def blender_check(workspace, blender, catalog, scene=None, expected_meshes=None):
    if list(sys.version_info[:2]) not in catalog["runner_python_versions"]:
        raise ValueError("Use Python 3.11 or 3.12, or otw.ps1 with Blender's bundled Python.")
    version = subprocess.run([str(blender), "--version"], capture_output=True, text=True, timeout=30, check=True)
    match = re.search(r"^Blender (\d+\.\d+\.\d+)\b", version.stdout, re.MULTILINE)
    if not match or match.group(1) != catalog["blender_version"]:
        raise ValueError("Blender version mismatch: exactly " + catalog["blender_version"] + " is required")
    folder = unique_folder(workspace, "checks", "scene" if scene else "doctor")
    folder.mkdir()
    report_path = folder / "report.json"
    command = [str(blender), "--factory-startup", "--background", "--disable-autoexec", "--python-exit-code", "1",
               "--python", str(ROOT / "scripts/workspace_blender.py"), "--", "--report", str(report_path)]
    if scene:
        command.extend(["--input", str(scene)])
    with (folder / "blender.log").open("w", encoding="utf-8") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
    if result.returncode or not report_path.is_file():
        raise ValueError("Blender check failed; see " + str(folder / "blender.log"))
    report = read_json(report_path)
    if not report.get("ok") or report["blender_version"] != catalog["blender_version"]:
        raise ValueError("Blender runtime/reference verification failed")
    if expected_meshes is not None and report["scene"]["meshes"] != expected_meshes:
        raise ValueError("Unexpected scene mesh count")
    report["runner_python"] = sys.version.split()[0]
    report["host_platform"] = sys.platform
    report["checked_on_current_host_only"] = True
    write_json(report_path, report)
    return {"report": report_path.relative_to(workspace).as_posix(), "blender_version": report["blender_version"],
            "blender_python": report["blender_python"], "scene": report.get("scene")}


def fetch_sources(workspace, catalog, inputs=None):
    source = catalog["sources"]["plateau-minato-2025"]
    destination = inside(workspace, "sources/plateau-minato-2025")
    for name, specification in source["files"].items():
        path = inside(destination, name)
        if inputs:
            copy_verified(Path(inputs) / name, path, specification)
        else:
            fetch_file(path, specification)
    notice = inside(ROOT, source["notice"])
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "NOTICE.md").write_bytes(notice.read_bytes())
    write_json(destination / "source-record.json", {"files": source["files"], "notice": source["notice"],
               "input_mode": "explicit-pinned-files" if inputs else "official-download-or-verified-workspace-files"})
    return destination


def save_profile(workspace, profile, record):
    path = inside(workspace, "workspace.json")
    state = read_json(path) if path.exists() else {"schema_version": 1, "profiles": {}}
    if state.get("schema_version") != 1:
        raise ValueError("Unknown workspace state version")
    state["profiles"][profile] = record
    write_json(path, state)


class CityUpdateRequired(ValueError):
    """The registered full-city scene differs from the current accepted asset."""


def registered_profile(workspace, profile, catalog):
    state_path = inside(workspace, "workspace.json")
    record = read_json(state_path).get("profiles", {}).get(profile) if state_path.exists() else None
    if not record:
        if profile == "city":
            raise ValueError("Full city is unavailable: public distribution is not ready. Obtain the approved scene from an authorized provider and run import-city --input PATH. Mori is a separate limited profile.")
        raise ValueError("Mori is not built. Run setup --profile mori.")
    if record["scene"] not in record["files"]:
        raise ValueError("Scene is missing from the workspace integrity record")
    if profile == "city" and record["files"][record["scene"]] != catalog["profiles"]["city"]["asset"]:
        raise CityUpdateRequired("Registered city differs from the current accepted version. "
                                 "Run import-city --input PATH with the current approved scene. "
                                 "Previous models and edits are preserved.")
    for relative, expected in record["files"].items():
        verify_file(inside(workspace, relative), expected)
    scene = inside(workspace, record["scene"])
    if profile == "city":
        verify_file(scene, catalog["profiles"]["city"]["asset"])
    return record, scene


def file_specs(workspace, paths):
    return {path.relative_to(workspace).as_posix(): {"bytes": path.stat().st_size, "sha256": digest(path)} for path in paths}


def import_city(workspace, source, blender, catalog):
    profile = catalog["profiles"]["city"]
    scene = inside(workspace, f"assets/tokyo-city/{profile['asset']['sha256']}/city.blend")
    copy_verified(source, scene, profile["asset"])
    check = blender_check(workspace, blender, catalog, scene, profile["expected_meshes"])
    verify_file(scene, profile["asset"])
    record = {"scene": scene.relative_to(workspace).as_posix(), "files": file_specs(workspace, [scene]),
              "runtime_check": check, "distribution": profile["distribution"], "evidence": profile["evidence"]}
    save_profile(workspace, "city", record)
    return record


def setup_mori(workspace, blender, catalog, inputs=None):
    check = blender_check(workspace, blender, catalog)
    sources = fetch_sources(workspace, catalog, inputs)
    output = unique_folder(workspace, "builds", "mori")
    profile = catalog["profiles"]["mori"]
    command = [sys.executable, str(inside(ROOT, profile["runner"])), "--blender", str(blender),
               "--inputs", str(sources), "--output", str(output)]
    print("Building Mori neighborhood in " + str(output), flush=True)
    subprocess.run(command, cwd=ROOT, timeout=3900, check=True)
    result = read_json(output / "run.json")
    if not result.get("ok") or not result.get("licensed_parts_verified"):
        raise ValueError("Mori generation/part-scope validation failed")
    for stage in ("before", "after"):
        if not result["validation"][stage].get("ok"):
            raise ValueError("Mori saved-scene validation failed")
    if result["validation"]["after"]["meshes"] != profile["expected_meshes"]:
        raise ValueError("Unexpected Mori mesh count")
    if not (output / profile["scene"]).is_file():
        raise ValueError("Missing generated scene; workspace was not registered")
    paths = sorted(p for p in output.iterdir() if p.is_file() and p.suffix in {".blend", ".png", ".json", ".md", ".txt", ".html"})
    record = {"scene": (output / profile["scene"]).relative_to(workspace).as_posix(),
              "review": (output / "review.html").relative_to(workspace).as_posix(),
              "files": file_specs(workspace, paths), "source_code_sha256": result["code_sha256"],
              "catalog_sha256": digest(CATALOG), "runtime_check": check, "distribution": profile["distribution"]}
    save_profile(workspace, "mori", record)
    return record


def prepare_edit(workspace, profile, catalog):
    record, source = registered_profile(workspace, profile, catalog)
    output = unique_folder(workspace, "edits", profile)
    output.mkdir()
    destination = output / "scene.blend"
    copy_verified(source, destination, record["files"][record["scene"]])
    for relative in record["files"]:
        item = inside(workspace, relative)
        if item.suffix in {".md", ".txt"} or item.name in {"provenance.json", "plaza-provenance.json"}:
            shutil.copyfile(item, output / item.name)
    write_json(output / "edit.json", {"profile": profile, "reference_scene": record["scene"],
               "reference_sha256": digest(source), "scene": "scene.blend", "validated_edit": False,
               "distribution_lock": record.get("distribution_lock"),
               "district_build_id": record.get("district_build_id"),
               "note": "This is an editable copy. Reference validation does not validate later edits. Use evidence-backed changes and a matching review configuration."})
    return destination


def review_city(workspace, blender, catalog, device):
    _, scene = registered_profile(workspace, "city", catalog)
    profile = catalog["profiles"]["city"]
    folder = unique_folder(workspace, "reviews", "city")
    config = unique_folder(workspace, "review-configs", "city")
    config.mkdir()
    features = read_json(inside(ROOT, profile["features"]))
    features["waiver_input_sha256"] = profile["asset"]["sha256"]
    write_json(config / "features.json", features)
    write_json(config / "lock.json", {**profile["asset"], "blender_version": catalog["blender_version"] + " LTS"})
    subprocess.run([sys.executable, str(ROOT / "scripts/review.py"), "--blender", str(blender), "--input", str(scene),
                    "--lock", str(config / "lock.json"), "--features", str(config / "features.json"),
                    "--cameras", str(inside(ROOT, profile["cameras"])), "--output", str(folder),
                    "--device", device, "--width", "640", "--height", "360", "--samples", "8", "--timeout", "1200"],
                   cwd=ROOT, check=True, timeout=6200)
    return {"review": str(folder / "review.html"), "mode": "baseline-capture; no model edits"}


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "district":
        from district_distribution import main as district_main
        return district_main(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--workspace", type=Path, default=ROOT / "data/local")
    common.add_argument("--blender", type=Path)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("district", help="Select, lock, fetch and build districts/shared packages (district --help)")
    for name in ("status", "doctor", "fetch", "fetch-production", "import-production-inputs", "setup", "import-city", "verify", "edit", "review"):
        command = sub.add_parser(name, parents=[common])
        if name in {"setup", "verify", "edit"}:
            command.add_argument("--profile", choices=["city", "mori"], default="city")
        if name in {"fetch", "setup"}:
            command.add_argument("--inputs", type=Path, help="Explicit directory containing the two exact official files")
        if name == "fetch-production":
            command.add_argument("--inputs", type=Path, help="Explicit directory containing the pinned historical source files")
        if name in {"import-city", "import-production-inputs"}:
            command.add_argument("--input", required=True, type=Path)
        if name == "import-production-inputs":
            command.add_argument("--include-scenes", action="store_true", help="Also copy the five intermediate blends (about 2.76 GB)")
        if name == "edit":
            command.add_argument("--open", action="store_true", help="Open the new editable copy in Blender")
        if name == "review":
            command.add_argument("--device", choices=["CPU", "OPTIX"], default="CPU")
    args = parser.parse_args(argv)
    catalog, workspace = load_catalog(), args.workspace.resolve()
    try:
        if args.command == "status":
            result = {"workspace": str(workspace), "profiles": {}, "full_city_publicly_available": False}
            for profile in catalog["profiles"]:
                try:
                    _, scene = registered_profile(workspace, profile, catalog)
                    result["profiles"][profile] = {"ready_locally": True, "scene": str(scene)}
                except (ValueError, OSError, KeyError) as error:
                    result["profiles"][profile] = {"ready_locally": False, "reason": str(error)}
                    if isinstance(error, CityUpdateRequired):
                        result["profiles"][profile]["update_required"] = True
                result["profiles"][profile]["label"] = catalog["profiles"][profile]["label"]
        elif args.command == "fetch":
            result = {"sources": str(fetch_sources(workspace, catalog, args.inputs))}
        elif args.command == "fetch-production":
            from fetch_legacy_production import fetch
            result = {"sources": str(fetch(inside(workspace, "sources/legacy-production-defac576"), args.inputs)),
                      "purpose": "Source inspection; no legacy code execution or city generation"}
        elif args.command == "import-production-inputs":
            from import_legacy_inputs import import_inputs
            result = import_inputs(args.input, inside(workspace, "sources/legacy-production-inputs-v1"), args.include_scenes)
        elif args.command == "setup" and args.profile == "city":
            # Do this first: never quietly build a different city when this is unavailable.
            if args.inputs:
                raise ValueError("--inputs is only supported by the Mori profile; use import-city for the full city")
            _, scene = registered_profile(workspace, "city", catalog)
            result = blender_check(workspace, find_blender(args.blender), catalog, scene, catalog["profiles"]["city"]["expected_meshes"])
        elif args.command == "edit":
            blender = find_blender(args.blender) if args.open else None
            if blender:
                blender_check(workspace, blender, catalog)
            destination = prepare_edit(workspace, args.profile, catalog)
            if args.open:
                subprocess.Popen([str(blender), "--disable-autoexec", str(destination)])
            result = {"editable_copy": str(destination), "opened": args.open}
        else:
            blender = find_blender(args.blender)
            if args.command == "doctor":
                result = blender_check(workspace, blender, catalog)
            elif args.command == "import-city":
                result = import_city(workspace, args.input, blender, catalog)
            elif args.command == "setup":
                result = setup_mori(workspace, blender, catalog, args.inputs)
            elif args.command == "verify":
                _, scene = registered_profile(workspace, args.profile, catalog)
                result = blender_check(workspace, blender, catalog, scene, catalog["profiles"][args.profile]["expected_meshes"])
            else:
                result = review_city(workspace, blender, catalog, args.device)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, KeyError, subprocess.SubprocessError) as error:
        print("Workspace error: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

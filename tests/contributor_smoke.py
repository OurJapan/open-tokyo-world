# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Fresh public-data onboarding check, including a disposable edit/save/reopen."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def isolated_environment(output):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("BLENDER_") or key in {
            "PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP", "GH_TOKEN", "GITHUB_TOKEN", "OTW_BLENDER",
        }:
            env.pop(key)
    env.update(PYTHONNOUSERSITE="1", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    for key in ("BLENDER_USER_CONFIG", "BLENDER_USER_SCRIPTS", "BLENDER_USER_DATAFILES", "BLENDER_USER_EXTENSIONS"):
        folder = output / "blender-profile" / key.lower()
        folder.mkdir(parents=True)
        env[key] = str(folder)
    return env


def verify(blender, output, repo):
    output.mkdir(parents=True, exist_ok=False)
    (output / "logs").mkdir()
    env = isolated_environment(output)
    workspace = output / "workspace"
    lock_path = output / "selection.json"
    started = time.monotonic()
    github = os.environ.get("GITHUB_ACTIONS") == "true"
    run_url = (os.environ.get("GITHUB_SERVER_URL", "https://github.com") + "/" + os.environ["GITHUB_REPOSITORY"]
               + "/actions/runs/" + os.environ["GITHUB_RUN_ID"]) if github else None
    report = {"schema_version": 1, "ok": False, "platform": sys.platform,
              "runner_python": sys.version.split()[0], "github_actions": github, "run_url": run_url,
              "fresh_workspace": True, "isolated_blender_user_directories": True,
              "explicit_local_source_directories": [], "automatic_script_execution": False,
              "scope": "Mori neighborhood and published shared components; automated headless checks",
              "limitations": ["No interactive desktop/GPU performance or first-time human usability test.",
                              "No full-city distribution, geographic accuracy or cross-host byte-identical render claim.",
                              "On a local run, file/profile isolation is not an OS or hardware sandbox."]}

    def command(label, args, timeout=4200):
        print(label, flush=True)
        log = output / "logs" / (label + ".log")
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(args, cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        if result.returncode:
            raise RuntimeError(label + " failed; see " + str(log))
        return log

    def cli(label, *args):
        log = command(label, [sys.executable, str(repo / "scripts/workspace.py"), *args,
                             "--workspace", str(workspace), "--blender", str(blender)])
        text = log.read_text(encoding="utf-8-sig")
        return json.loads(text[text.index("{"):])

    try:
        cli("doctor", "doctor")
        plan = cli("plan", "district", "plan", "--district", "mori", "--common", "procedural-components", "--output", str(lock_path))
        first = cli("setup", "district", "setup", "--lock", str(lock_path))
        if not first["ok"] or first["download_bytes"] != plan["unique_bytes"] or first["local_copy_bytes"]:
            raise ValueError("Fresh setup did not use only new public downloads")
        if first["districts"]["mori"]["reused"] or any(item["state"] != "download" for item in first["files"]):
            raise ValueError("Unexpected preexisting cache/build")
        reference = Path(first["districts"]["mori"]["scene"])
        kit = Path(first["scenes"]["procedural-components"])
        reference_hash, kit_hash = digest(reference), digest(kit)
        run = read(reference.parent / "run.json")
        if not run["ok"] or run["legacy_scene_used"] or run["validation"]["after"]["meshes"] != 42:
            raise ValueError("Mori validation failed")
        images = sorted(path.name for path in reference.parent.glob("*.png"))
        if len(images) != 8:
            raise ValueError("Expected eight comparison images")
        reused = cli("offline-reuse", "district", "setup", "--lock", str(lock_path), "--offline")
        if not reused["ok"] or reused["download_bytes"] or reused["local_copy_bytes"]:
            raise ValueError("Offline reuse unexpectedly required data")
        if not reused["districts"]["mori"]["reused"] or reused["districts"]["mori"]["scene"] != str(reference):
            raise ValueError("Did not reuse the generated reference")
        edit = cli("edit-copy", "district", "edit", "--lock", str(lock_path))
        copy = Path(edit["editable_copy"])
        if copy == reference or digest(copy) != reference_hash:
            raise ValueError("Editable copy differs from reference")
        notices = [path.name for path in reference.parent.iterdir() if path.suffix in {".md", ".txt"}]
        for name in notices:
            if digest(copy.parent / name) != digest(reference.parent / name):
                raise ValueError("Attribution did not survive copying")
        saved = copy.with_name("onboarding-test-only.blend")
        intent, outcome = output / "edit-intent.json", output / "edit-result.json"
        worker = ROOT / "tests/contributor_edit_blender.py"
        base = [str(blender), "--factory-startup", "--background", "--disable-autoexec",
                "--python-exit-code", "1", "--python", str(worker), "--"]
        command("edit-save", base + ["edit", "--input", str(copy), "--output", str(saved), "--record", str(intent)], 600)
        command("edit-reopen", base + ["reopen", "--input", str(saved), "--record", str(intent), "--result", str(outcome)], 600)
        roundtrip = read(outcome)
        if not roundtrip["ok"] or digest(reference) != reference_hash or digest(copy) != reference_hash or digest(kit) != kit_hash:
            raise ValueError("Round trip failed or protected inputs changed")
        verified = cli("reference-verify", "district", "verify", "--lock", str(lock_path))
        if not verified["ok"]:
            raise ValueError("Reference verification failed after editing")
        lock = read(lock_path)
        report.update(ok=True, lock_id=first["lock_id"], code_sha256_lf=lock["code_sha256_lf"],
            downloads=first["files"], download_bytes=first["download_bytes"], local_copy_bytes=0,
            offline_download_bytes=0, generated_reference_reused=True,
            mori_meshes=42, comparison_pngs=images,
            shared_meshes=first["shared_scene_checks"]["procedural-components"]["scene"]["meshes"],
            edit_roundtrip=roundtrip, reference_unchanged=True, shared_kit_unchanged=True,
            notices_preserved=sorted(notices), legacy_scene_used=False)
    except Exception as error:
        # Full diagnostics remain in logs; the portable report avoids local paths.
        report["failure_type"] = type(error).__name__
        raise
    finally:
        report["elapsed_seconds"] = round(time.monotonic() - started, 3)
        (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "report": str(output / "report.json"),
                      "download_bytes": report["download_bytes"], "edit_saved_and_reopened": roundtrip["ok"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--blender", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True, help="New directory; existing outputs are never reused")
    parser.add_argument("--repo", type=Path, default=ROOT, help="Source checkout/archive to test; defaults to this repository")
    args = parser.parse_args()
    verify(args.blender.resolve(), args.output.resolve(), args.repo.resolve())

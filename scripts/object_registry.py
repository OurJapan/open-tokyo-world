# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
"""Compile a version-pinned, object-type-independent assembly plan; no asset execution."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path


class ContractError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ContractError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf8")


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def keyed(records, label):
    result = {}
    for record in records:
        key = record.get("id")
        require(isinstance(key, str) and key and key not in result, "Missing/duplicate " + label)
        result[key] = record
    return result


def sha(value):
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def validate(registry):
    require(registry.get("schema_version") == 1, "Unsupported schema version")
    frames = keyed(registry["frames"], "frame")
    for frame in frames.values():
        require(frame.get("units") == "m" and frame.get("axes") == "east-north-up", "Unsupported coordinate convention")
        require(bool(frame.get("definition")), "Missing coordinate definition")
    sources = keyed(registry["sources"], "source")
    for source in sources.values():
        require(bool(source.get("revision")) and sha(source.get("sha256")), "Source must be revision/hash pinned")
        require(bool(source.get("license")) and bool(source.get("attribution")), "Source rights missing")
    models = keyed(registry["models"], "model")
    for model in models.values():
        require(bool(model.get("version")) and sha(model.get("sha256")), "Model must be version/hash pinned")
        require(bool(model.get("license")) and bool(model.get("attribution")), "Model rights missing")
        require(model.get("source_refs") and all(s in sources for s in model["source_refs"]), "Unknown model source")
        require(model.get("format") in {"blend", "glb", "mesh-json"}, "Unsupported model format")
        require(bool(model.get("locator")), "Missing model locator")
    features = keyed(registry["features"], "feature")
    for feature in features.values():
        require(bool(feature.get("kind")) and bool(feature.get("owner_area")), "Missing feature classification/owner")
        require(feature.get("frame") in frames, "Unknown coordinate frame")
        require(feature.get("source_refs") and all(s in sources for s in feature["source_refs"]), "Unknown feature source")
        require(all(i in features for i in feature.get("review_neighbors", [])), "Unknown review neighbor")
        parent = feature.get("parent")
        require(parent is None or parent in features, "Unknown parent")
        seen = {feature["id"]}
        while parent is not None:
            require(parent not in seen, "Parent cycle")
            seen.add(parent)
            parent = features[parent].get("parent")
        parts = keyed(feature["parts"], "part")
        require(bool(parts), "Feature has no parts")
        for part in parts.values():
            binding = part.get("source_binding")
            if binding:
                require(binding.get("source") in sources and bool(binding.get("object_id")), "Invalid source binding")
                require(binding["object_id"] in sources[binding["source"]].get("object_ids", []), "Source object missing from pinned import inventory")
        revisions = keyed(feature["revisions"], "revision")
        for revision in revisions.values():
            require(revision.get("status") in {"candidate", "accepted"}, "Unknown review status")
            slots = set()
            for operation in revision["operations"]:
                action = operation.get("action")
                require(action in {"add", "replace", "suppress", "material"}, "Unknown operation")
                part = operation.get("part")
                require(part in parts, "Unknown part; segment source roads explicitly first")
                slot = (part, "material" if action == "material" else "geometry")
                require(slot not in slots, "Conflicting operations within revision")
                slots.add(slot)
                if action != "suppress":
                    variants = operation.get("models", {})
                    require(bool(variants) and all(v in models for v in variants.values()), "Unknown representation model")
                if action in {"add", "replace"}:
                    position = operation.get("position_m")
                    require(isinstance(position, list) and len(position) == 3 and all(type(x) in (int, float) and math.isfinite(x) for x in position), "Invalid position")
                    angle = operation.get("yaw_degrees")
                    require(type(angle) in (int, float) and math.isfinite(angle), "Invalid yaw")
                if action == "material":
                    require(bool(operation.get("slot")), "Material slot must be explicit")
    return frames, sources, models, features


def compile_plan(registry, lock, *, allow_candidates=False):
    registry = copy.deepcopy(registry)
    frames, sources, models, features = validate(registry)
    require(lock.get("schema_version") == 1 and lock.get("registry_sha256") == digest(registry), "Registry lock mismatch")
    require(lock.get("frame") in frames, "Unknown assembly frame")
    profile = lock.get("profile")
    require(isinstance(profile, str) and bool(profile), "Missing representation profile")
    selections = lock["selections"]
    require(bool(selections) and len({s["feature"] for s in selections}) == len(selections), "Duplicate/empty feature selection")
    states, claims, used_models, selected, dependencies, review = {}, {}, {}, {}, {}, set()
    operations = []
    for selection in selections:
        fid = selection["feature"]
        require(fid in features, "Unknown selected feature")
        feature = features[fid]
        require(feature["frame"] == lock["frame"], "Explicit coordinate migration required; no implicit transform")
        revisions = keyed(feature["revisions"], "revision")
        require(selection["revision"] in revisions, "Unknown selected revision")
        revision = revisions[selection["revision"]]
        require(allow_candidates or revision["status"] == "accepted", "Candidate requires explicit review mode")
        selected[fid] = revision["id"]
        dependencies[fid] = revision.get("requires", [])
        review.update([fid, *feature.get("review_neighbors", [])])
        parts = keyed(feature["parts"], "part")
        for pid, part in parts.items():
            binding = part.get("source_binding")
            if binding:
                claim = (binding["source"], binding["object_id"])
                require(claim not in claims, "Source object claimed twice; split into distinct source parts before registration")
                claims[claim] = (fid, pid)
            states[(fid, pid)] = {"feature": fid, "part": pid, "kind": feature["kind"], "owner_area": feature["owner_area"], "geometry": {"source_binding": binding} if binding else None, "material": None}
        for operation in revision["operations"]:
            state = states[(fid, operation["part"])]
            action = operation["action"]
            model = None
            if action != "suppress":
                require(profile in operation["models"], "Representation profile missing; no implicit fallback")
                mid = operation["models"][profile]
                model = models[mid]
                used_models[mid] = model
            if action == "add":
                require(state["geometry"] is None, "Add would duplicate existing source geometry")
            elif action in {"replace", "suppress"}:
                require(state["geometry"] is not None, "Replacement/suppression target missing")
            elif action == "material":
                require(state["geometry"] is not None, "Material target missing or suppressed")
            if action in {"add", "replace"}:
                state["geometry"] = {"model": mid, "position_m": operation["position_m"], "yaw_degrees": operation["yaw_degrees"]}
            elif action == "suppress":
                require(state["material"] is None, "Suppression conflicts with material override")
                state["geometry"] = None
            else:
                state["material"] = {"model": mid, "slot": operation["slot"]}
            operations.append({"feature": fid, "revision": revision["id"], **operation})
    for fid, requirements in dependencies.items():
        for requirement in requirements:
            require(selected.get(requirement["feature"]) == requirement["revision"], "Missing or wrong dependent feature revision")
    visiting, done, build_order = set(), set(), []
    def visit(fid):
        require(fid not in visiting, "Dependency cycle")
        if fid in done:
            return
        visiting.add(fid)
        for requirement in dependencies[fid]:
            visit(requirement["feature"])
        visiting.remove(fid)
        done.add(fid)
        build_order.append(fid)
    for fid in selected:
        visit(fid)
    used_sources = set()
    for fid in selected:
        used_sources.update(features[fid]["source_refs"])
        used_sources.update(p['source_binding']['source'] for p in features[fid]['parts'] if p.get('source_binding'))
    for model in used_models.values():
        used_sources.update(model["source_refs"])
    return {"schema_version": 1, "registry_sha256": digest(registry), "lock_sha256": digest(lock), "review_only": allow_candidates,
            "frame": frames[lock["frame"]], "profile": profile, "selected": selected,
            "parts": sorted(states.values(), key=lambda p: (p["feature"], p["part"])),
            "operations": operations, "models": used_models, "dependencies": dependencies,
            "build_order": build_order, "review_neighbors": {fid: features[fid].get("review_neighbors", []) for fid in selected},
            "sources": {sid: sources[sid] for sid in sorted(used_sources)}, "review_features": sorted(review),
            "limitations": ["Plan only: not a Blender assembly or geometry validation", "Source objects must be atomized before partial replacement", "No implicit datum conversion or network topology validation"]}


def affected_features(old, new):
    """Reverse dependencies + declared neighbors; conservatively reports changed model content."""
    changed = {p["feature"] for p in old["parts"] + new["parts"] if p not in old["parts"] or p not in new["parts"]}
    mids = {m for m in set(old["models"]) | set(new["models"]) if old["models"].get(m) != new["models"].get(m)}
    for p in old["parts"] + new["parts"]:
        if any(p.get(field) and p[field].get("model") in mids for field in ["geometry", "material"]):
            changed.add(p["feature"])
    # Full review scope is returned conservatively when the locked source/frame changes.
    if old["sources"] != new["sources"] or old["frame"] != new["frame"]:
        return sorted(set(old["review_features"]) | set(new["review_features"]))
    for fid in set(old["selected"]) | set(new["selected"]):
        if (old["selected"].get(fid) != new["selected"].get(fid)
                or old["dependencies"].get(fid) != new["dependencies"].get(fid)
                or old["review_neighbors"].get(fid) != new["review_neighbors"].get(fid)):
            changed.add(fid)
    while True:
        expanded = set(changed)
        for plan in [old, new]:
            for fid, required in plan["dependencies"].items():
                if any(r["feature"] in changed for r in required):
                    expanded.add(fid)
            for fid in changed:
                expanded.update(plan["review_neighbors"].get(fid, []))
        if expanded == changed:
            return sorted(changed)
        changed = expanded


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--lock", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--review-candidates", action="store_true")
    args = parser.parse_args()
    registry = json.loads(args.registry.read_text(encoding="utf8"))
    lock = json.loads(args.lock.read_text(encoding="utf8"))
    result = compile_plan(registry, lock, allow_candidates=args.review_candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(args.output)


if __name__ == "__main__":
    main()

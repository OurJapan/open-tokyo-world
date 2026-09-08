# SPDX-License-Identifier: MIT
# Copyright (c) 2026 ark4ez
import copy
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from object_registry import ContractError, compile_plan, digest, affected_features


class ObjectRegistryTests(unittest.TestCase):
    def setUp(self):
        self.r = json.loads((ROOT / "registry/example.json").read_text())
        self.lock = json.loads((ROOT / "registry/example.lock.json").read_text())

    def plan(self):
        self.lock["registry_sha256"] = digest(self.r)
        return compile_plan(self.r, self.lock)

    def reject(self):
        with self.assertRaises(ContractError):
            self.plan()

    def test_mixed_types_and_shared_model_instances(self):
        p = self.plan()
        self.assertEqual(len(p["selected"]), 7)
        self.assertEqual(len({x["kind"] for x in p["parts"]}), 6)
        benches = [x for x in p["parts"] if x["kind"] == "street-furniture"]
        self.assertEqual(benches[0]["geometry"]["model"], benches[1]["geometry"]["model"])
        self.assertNotEqual(benches[0]["geometry"]["position_m"], benches[1]["geometry"]["position_m"])

    def test_partial_road_preserves_other_segment_geometry(self):
        p = self.plan()
        road = {x["part"]:x for x in p["parts"] if x["feature"] == "fixture:road"}
        self.assertIn("model", road["segment-a"]["geometry"])
        self.assertEqual(road["segment-b"]["geometry"]["source_binding"]["object_id"], "road-1/segment-b")
        self.assertEqual(road["segment-b"]["material"]["slot"], "paving")

    def test_rollback_changes_only_target_and_declared_review_scope(self):
        feature = self.r["features"][1]
        feature["revisions"].append({"id":"baseline","status":"accepted","operations":[]})
        # Both locks use the same registry, so reverting a selected revision is sufficient.
        self.r["features"][3]["revisions"][0]["requires"] = []
        before = self.plan()
        self.lock["selections"][1]["revision"] = "baseline"
        after = self.plan()
        self.assertEqual(affected_features(before, after), ["fixture:bench-1", "fixture:road"])
        self.assertEqual([p for p in before["parts"] if p["feature"] != "fixture:road"], [p for p in after["parts"] if p["feature"] != "fixture:road"])

    def test_missing_model(self):
        self.r["models"].pop(0); self.reject()

    def test_unpinned_model(self):
        self.r["models"][0]["sha256"] = "latest"; self.reject()

    def test_missing_rights(self):
        self.r["models"][0]["license"] = ""; self.reject()

    def test_wrong_registry_lock(self):
        self.lock["registry_sha256"] = "0" * 64
        with self.assertRaises(ContractError): compile_plan(self.r, self.lock)

    def test_duplicate_selection(self):
        self.lock["selections"].append(self.lock["selections"][0]); self.reject()

    def test_source_object_not_in_import_inventory(self):
        self.r["features"][0]["parts"][0]["source_binding"]["object_id"] = "invented"; self.reject()

    def test_duplicate_source_claim(self):
        self.r["features"][6]["parts"][0]["source_binding"] = copy.deepcopy(self.r["features"][0]["parts"][0]["source_binding"]); self.reject()

    def test_unknown_road_segment(self):
        self.r["features"][1]["revisions"][0]["operations"][0]["part"] = "half-by-distance"; self.reject()

    def test_conflicting_operations(self):
        ops = self.r["features"][1]["revisions"][0]["operations"]
        ops.append(copy.deepcopy(ops[0])); self.reject()

    def test_add_over_existing(self):
        self.r["features"][0]["revisions"][0]["operations"][0]["action"] = "add"; self.reject()

    def test_replace_missing(self):
        self.r["features"][2]["revisions"][0]["operations"][0]["action"] = "replace"; self.reject()

    def test_material_on_suppressed(self):
        self.r["features"][6]["revisions"][0]["operations"].append({"action":"material","part":"whole","models":{"review":"fixture:paving-material"},"slot":"paving"}); self.reject()

    def test_frame_mismatch(self):
        self.r["frames"].append({"id":"other","units":"m","axes":"east-north-up","definition":"other origin"})
        self.r["features"][0]["frame"] = "other"; self.reject()

    def test_nan_position(self):
        self.r["features"][0]["revisions"][0]["operations"][0]["position_m"][0] = float("nan"); self.reject()

    def test_missing_lod_no_fallback(self):
        self.lock["profile"] = "far"; self.reject()

    def test_candidate_opt_in(self):
        self.r["features"][0]["revisions"][0]["status"] = "candidate"
        self.reject()
        self.assertTrue(compile_plan(self.r, self.lock, allow_candidates=True)["review_only"])

    def test_dependency_version(self):
        self.r["features"][3]["revisions"][0]["requires"][0]["revision"] = "wrong"; self.reject()

    def test_dependency_cycle(self):
        self.r["features"][1]["revisions"][0]["requires"] = [{"feature":"fixture:bench-1","revision":"v1"}]; self.reject()

    def test_parent_cycle(self):
        self.r["features"][0]["parent"] = "fixture:road"
        self.r["features"][1]["parent"] = "fixture:building"; self.reject()

    def test_shared_model_change_invalidates_instances(self):
        before = self.plan()
        self.r["models"][3]["sha256"] = "0" * 64
        after = self.plan()
        self.assertEqual(affected_features(before, after), ["fixture:bench-1", "fixture:bench-2"])

    def test_source_change_expands_review(self):
        before = self.plan()
        self.r["sources"][0]["sha256"] = "0" * 64
        after = self.plan()
        self.assertEqual(affected_features(before, after), before["review_features"])

    def test_deterministic_and_no_input_mutation(self):
        registry = copy.deepcopy(self.r)
        self.assertEqual(self.plan(), self.plan())
        self.assertEqual(registry, self.r)


if __name__ == "__main__":
    unittest.main()

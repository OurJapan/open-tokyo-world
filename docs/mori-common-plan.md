# Mori standalone consumer for the common feature plan

Issue #34 connects the existing standalone Mori recipe to `object_registry.compile_plan`.
It does not change the geometry or integrate the full city. The default input is the
same pinned Minato 2025 data221 tile and tileset, with 24 source buildings.

## Contract and execution

- [Inventory](../sources/plateau-minato-2025-data221.json): the 24 `gml_id` values,
  in batch-table order, extracted from the hash-verified official tile.
- [Registry](../registry/mori.json) and [lock](../registry/mori.lock.json): one selected
  Mori revision, 23 review neighbors, suppression of one source building and addition
  of 13 named stable parts. `accepted` denotes the existing standalone recipe, not
  survey accuracy or acceptance into the full city.
- [Procedural manifest](../starter/mori/model-manifest.json): an exact object-name
  to stable part-ID contract and LF-normalized hashes of all 18 Python execution files.
  Its own hash and the inventory hash identify exact JSON bytes, kept LF by `.gitattributes`.
- [Adapter](../starter/mori/plan_adapter.py): allows only this source, frame, profile,
  revision, model, locator, operation sequence, placement and part set. It never
  imports or executes a locator. The generic planner only records the new
  `procedural-manifest` format and retains original source bindings after suppression.

```sh
python starter/mori/run.py --blender BLENDER --inputs PINNED_INPUT_DIRECTORY --output data/local/mori-plan-run
# Optional explicit copies of the same supported registry/lock:
python starter/mori/run.py --blender BLENDER --registry registry/mori.json --lock registry/mori.lock.json --output data/local/mori-plan-download
```

The runner compiles and checks the contract, code hashes and both source files
before creating the output directory or launching Blender. A failure is reported
on stderr with a nonzero exit code; there is deliberately no output `run.json` for
a preflight rejection. Accepted inputs are retained as bytes for the build; the
registry, lock, manifest and compiled plan are copied into the result.

The worker recompiles the copied registry/lock and compares the saved plan on every
invocation. It suppresses the plan's `source_gml_id`, assigns the plan's stable IDs
to exactly 13 parts, and records plan/model identity on the scene and parts. Separate
Blender processes reopen Before and After, verify those identities and fingerprints,
and render the existing four matched views. After preserves all 23 neighboring
buildings and six plaza parts, including mesh, UV, material and transform fingerprints.

District distribution uses recipe version `0.2.0`; its code lock now includes the
planner, adapter, registry, lock, inventory and model manifest. LF-normalized code
hashes agree with the procedural manifest. Existing district locks with changed
execution files are rejected, requiring a newly reviewed lock.

## Verification

Run portable contracts and the saved-blend rejection suite:

```sh
python -m unittest discover -s tests -v
python -m compileall -q scripts tests starter/mori
python tests/mori_standalone_blender.py --blender BLENDER --run data/local/mori-plan-run --output data/local/mori-plan-negative
```

[Recorded evidence](evidence/mori-common-plan-run.json) contains the validated code
hashes, plan/model identity, counts, camera settings, source hashes and result paths.
[Four-view comparison](../renders/previews/mori-common-plan/comparison.jpg) is a
reduced preview; original 960x720 PNGs and all blends remain ignored local files.

On the recorded candidate, 349 portable tests completed (341 passed, eight unrelated
optional-dependency tests skipped). Blender generation and all nine saved-artifact
negatives passed. Base main was independently regenerated under the same settings:
all eight decoded Before/After images are pixel-identical to the new consumer.
An offline `district setup --district mori` also completed with the new recipe lock
and the same plan identity.

The runner tests cover stale locks, relocked source hashes/inventory/target IDs,
part/model/locator/operation/placement/frame/profile/selection/review-scope mismatches,
candidate/review-only plans, altered manifest/code and corrupt source bytes. Rejections
assert that Blender and network calls were not made and the output parent was not
created (corrupt-source cases use explicit local inputs).

Saved-blend negatives cover missing roof, changed neighbor, broken glass material,
duplicated source, changed plaza, wrong part ID, wrong scene plan hash, changed saved
plan and changed manifest. Each must fail for its expected reason before rendering.

## Updating reviewed pins

Runtime never refreshes hashes. After an intentional recipe change, review the
code and part/source contract, update `model-manifest.json`'s `code_sha256_lf` from
`plan_adapter.code_hashes()`, update `registry/mori.json`'s model hash from the exact
manifest bytes, then update `mori.lock.json`'s registry hash using
`object_registry.digest(registry)`. Bump recipe/model versions for changed contracts,
regenerate the district lock and repeat the required Blender validation. Do not edit
historical licensing provenance to make its old snapshots match new code.

## Limits

Validation was performed on Windows 19KF with Blender 4.5.1; portable CI checks do
not provide independent Blender validation on another OS. Display heights, inferred
geometry and the existing limited neighborhood remain unchanged. This does not
establish real-world accuracy, grant new third-party rights, or complete distribution
of the combined model. No source assets, generated blends or full-size render sets
are committed.

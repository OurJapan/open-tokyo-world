# FootTown south stair handrail joint

One local defect in the accepted PR60 model: the outer stair handrail ends
at `(-8, -31.13, 5.45)` while the landing rail starts at
`(-7.8, -31.38, 5.45)`. The model gap is 0.320156 m. Append one capped
32 mm radius connector between these existing endpoints. The stairs,
landing, rail heights, building and other tower parts retain their geometry.

The generator appends the connector after the original geometry. The pinned
increment edits only `OTW Tokyo Tower structure / foottown-metal`, adding
16 vertices and 10 polygons, with no new object, material or collection.
The regression test traverses generated handrail endpoints from the stair
foot to the far landing end and checks the landing approach remains clear.
It fails on the original generator and passes after the repair.

PR60 also contains two unused material datablocks that Blender discards on a
normal subsequent save. The increment enables their fake-user persistence
flags so all 583 original materials survive, with their shaders unchanged.
The saved validator checks every material fingerprint and allows only those
two persistence flag changes. This preserves the input rather than deleting
its unused materials.

This is continuity of an existing inferred model, not a surveyed dimension,
reconstruction of an observed real handrail detail, or engineering certification.
The original PR60 photo/model assumptions and asset restrictions still apply.

## Reproduce

Use the immutable private PR60 saved candidate, SHA-256
`e4ecbdf02fb6217e67c111f284a2d905bb31f3521fbd380818e687ba5d85da97`.
No city blend or original texture is published.

Run each phase in a separate Blender 4.5.1 LTS process, in order:

```powershell
# Replace BLENDER and PR60_AFTER with authorized local paths.
# PHASE: build, validate, render-before, render-after
& BLENDER --factory-startup --background --threads 2 --disable-autoexec --python-exit-code 1 --python scripts/tower_south_handrail.py -- --phase PHASE --input PR60_AFTER --output data/local/south-handrail
python -m unittest discover -s tests
python -m compileall -q scripts tests
```

`validate` reopens the saved candidate, compares all object/asset fingerprints
and protected flags/metadata, checks every old target vertex/polygon/flag and
the exact new connector, and runs the existing seven-group FootTown geometry,
entrance, ground-contact and roof/stair-clearance checks. Read-only phases
check input/candidate file hashes. Output/report overwrites are refused.

The renders use all eight existing FootTown acceptance views plus one local
joint view, under matched camera, light, engine, seed and settings:
Cycles/OptiX, 640 x 424, 16 samples, seed 0. Human inspection of these new
renders is a technical review; final maintainer acceptance remains pending.

[Verification](tower-south-handrail-validation.json) contains code and file
hashes, test counts and render evidence. The PR publishes only the local
detail and south context pairs as small PNGs, code and metadata.

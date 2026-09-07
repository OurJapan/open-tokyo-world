# Provenance notice / 出典・依存関係

## Independent code

The four files listed in LICENSE.md were produced in the OurJapan development workflow using an AI agent, with human direction and review. The maintainer confirmed authority to license these independent contributions on 2026-09-07. Copyright display: ark4ez. The MIT grant applies to code, not to data merely referenced by it.

The plaza generators reuse the entrance coordinate transform and the terrace primitive mesh builder. Geometry uses numerical parameters and deterministic generation. Model dimensions, materials, plant species and placement details include estimates. The `apply` functions require existing Blender objects and baseline data; a standalone city rebuild is not provided by this grant. Other repository modules remain outside the grant unless separately licensed.

## Inherited placement and reference material

Entrance registration was derived from a legacy wall associated with `PLATEAU_data221`, batch 5. The saved `data221.b3dm` tile matched the recorded distribution URL byte-for-byte on 2026-09-07 (1,246,040 bytes; SHA-256 `dc8c7539b2bb22d8c6659689c37aafa53b4896650bbd6bcfe7f791ab8b1a38d2`). This is tile identity verification, not a complete reconstruction audit of the legacy scene.

Source: [3D都市モデル（Project PLATEAU）港区（2025年度）](https://www.geospatial.jp/ckan/dataset/plateau-13103-minato-ku-2025), under the [PLATEAU site policy](https://www.mlit.go.jp/plateau/site-policy/). The legacy import transformed coordinates and shifted each building base to a scene plane. OurJapan subsequently used that scene for placement. These additions are not official government models.

The plaza diagnosis and connection context used saved OpenStreetMap information: © OpenStreetMap contributors, [ODbL and attribution](https://www.openstreetmap.org/copyright). Ground height z=.11 is a legacy generator constant, not a surveyed elevation. No OSM coordinate dataset or road mesh is distributed by this change. Publication of derived data must be evaluated separately from licensing this code.

Visual references were linked in the existing modeling records: [Mori Building](https://www.mori.co.jp/projects/azabudaihills/facilities/), [official floor map](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html), [PCPA](https://pcparch.com/work/azabudai-hills), and [Nihon Sekkei](https://www.nihonsekkei.co.jp/projects/19811/). Those photographs and plans are not included or relicensed here. Their mention does not imply endorsement.

No third-party data license is replaced by the MIT license for the four independent implementations. Future contributors should follow CONTRIBUTING.md and record permission for their own changes.

## Standalone starter

The two additional MIT scripts in `starter/plaza/` regenerate six original procedural parts without the legacy city input. See the [asset grant](starter/plaza/ASSET-LICENSE.md) and [machine-readable provenance](starter/plaza/provenance.json). This starter supplies a new viewing setup, not a reconstruction of the full legacy scene.

## Standalone Mori consent and provenance

On 2026-09-07 the account holder confirmed authority to license the eleven identified code snapshots, including incorporated legacy-derived implementation, under MIT and the identified original Mori contributions under CC BY 4.0. [Scope and consent](starter/mori/provenance.json) / [asset grant](starter/mori/ASSET-LICENSE.md). Existing four-file MIT snapshots were checked and match; no new consent was required for them. Third-party inputs keep their conditions. Code publication approval for PR #28 and this separate license consent are distinct records.

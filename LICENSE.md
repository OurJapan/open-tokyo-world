# License scope / ライセンス適用範囲

This repository has a partial, file-specific license grant. It is not licensed as a whole under MIT.

## MIT: four independent Python implementations

The independent code in the following four files, as present in baseline commit `b7462dceb907ed38d07fa600e39c23527d5e2c2d`, is licensed under the [MIT License](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. The hashes identify that snapshot; they do not restrict modification or redistribution permitted by MIT. Retain the copyright and license notice when redistributing the covered code.

| File | SHA-256 (UTF-8 bytes, CRLF normalized to LF) |
|---|---|
| `scripts/mori_plaza_v1.py` | `b16a1179b14f9e56b615d818c06da11c7be77959c199e2d93c6ee4544076fc2c` |
| `scripts/mori_plaza_link_v1.py` | `c5e15978e47a7e4816001b175ead98d7445bf37828f48945f15915db639f4d37` |
| `scripts/mori_entrance_v1.py` | `f9ab6f5aa0ad9a1cd201c8b021e9893a411e9556afbc7bb877f558e6faa2fede` |
| `scripts/mori_terrace_v1.py` | `2056674560bbcd92503db2a5e8491eca0f2f21ab782ba9d332820b70a74d1a9d` |

対象は上記4ファイルの独自実装です。この版の利用・改変・再配布・商用利用をMITの条件で許諾します。ハッシュは対象版の特定用であり、改変禁止や追加制限ではありません。後続寄稿者の権利をこの表示で勝手に許諾しません。

## MIT: starter runner

The original `starter/plaza/package.py` and `tests/test_plaza_package.py` are also covered by MIT, copyright (c) 2026 ark4ez. These grants cover these named implementations, not unrelated repository files.

The original code in `starter/plaza/run.py` and `starter/plaza/scene.py`, marked with SPDX-License-Identifier: MIT and copyright (c) 2026 ark4ez, is also licensed under [MIT](MIT-LICENSE.txt). This does not extend the four-file snapshot grant above to unrelated later modifications.

## CC BY 4.0: six-part starter

The original six procedural parts, their materials, starter camera/lighting, previews, and documentation/metadata in `starter/plaza/` have the separate grant in [starter/plaza/ASSET-LICENSE.md](starter/plaza/ASSET-LICENSE.md). Preserve its source notices. Python code remains MIT.

## MIT: pinned PLATEAU import trial

The original implementations in `starter/plateau/run.py`, `starter/plateau/tile.py`, `starter/plateau/scene.py`, and `tests/test_plateau_tile.py` are licensed under the [MIT License](MIT-LICENSE.txt), copyright (c) 2026 ark4ez. This grant does not cover PLATEAU data, imagery, Blender or its installed Draco library. Keep the input-specific notices in `starter/plateau/NOTICE.md`; generated combined scenes do not receive a blanket MIT grant.

## Outside these grants

Except for the separately identified starter above, no license is granted here for other repository files, legacy city scenes, generated models, reference photos, textures, music, trademarks, PLATEAU data, OpenStreetMap data, or other third-party content. Any separately applicable license remains in effect. Execution of the covered code does not itself grant rights to its inputs or outputs. This scope document adds no conditions to the MIT grant for the covered code.

6部品のスターターに限ってCC BY 4.0を適用します。全都市モデルや他のコード・文書が一括してMIT／CC BYになったとは扱わないでください。

See [NOTICE](NOTICE.md) for provenance and operational dependencies. Attribution required by a third-party license must be retained when that data is used; those requirements are not additional restrictions on the independent MIT code.

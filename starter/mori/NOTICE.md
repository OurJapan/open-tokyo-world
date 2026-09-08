# 森JPタワー独立生成試験の出典・適用範囲

公式入力は `starter/plateau/NOTICE.md` に記載する港区2025の固定タイル。元のgml_id、座標変換、個別高さ移動はgeoreference.jsonに記録する。全体に一括MIT/CC BYを適用しない。

`facade.py`は旧プロジェクトの`work/interior_walk/glass_return.py`と`work/landmark_rebuild/build.py`から形状生成部分を切り出したもの。実行時の旧blend、profiles.json、ASTによるコード読込、映画用カメラ操作は除外した。旧コードの調査対象hashは調査記録に固定されている。2026-09-07の同意により、今回の対象ファイルへ取り込まれた旧実装を含めMITを適用する。旧ファイル全文への許諾拡張ではない。

頂部と材質には既存の`mori_crown_v2.py`、`mori_facade_v2.py`、`mori_crown_material.py`を使用する。低層部の隣接面検証は`mori_podium_v3.py`。これらとmori_shape.pyを含む11ファイルの対象版はroot LICENSE.mdのMIT対象。provenance.jsonに版と同意を記録する。

入口・テラス・広場の対象生成関数はroot LICENSE.mdの指定版MIT grantを保持する。森JPタワー13部品の独自追加部分・独自材質等にはASSET-LICENSE.mdのCC BY 4.0を適用する。公式の元形状・Textureなど第三者部分の条件は保持し、combined blend全体への一括許諾ではない。今回のコード変更はモデルや第三者TextureをGitへ同梱しない。

外観の参考はPelli Clarke & Partnersの麻布台ヒルズ公式プロジェクト写真、森ビル公式施設案内・フロアマップ、日本設計のプロジェクト資料。リンクは既存patches/mori-podium-repair-v3.jsonに保持している。参考写真をTextureとして取り込まない。頂部高さ、コース、ガラス値、植栽、配置、材質は推定を含む。公式の建物モデル・測量成果・実物と完全一致するモデルを名乗らない。

旧推定値に基づく床・天井・屋根の最小形状を含む。家具・屋上設備、旧道路端の修復、東京タワー本体は今回の生成対象外。旧承認済みシーンとの画面一致は保証しない。

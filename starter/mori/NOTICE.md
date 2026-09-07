# 森JPタワー独立生成試験の出典・適用範囲

公式入力は `starter/plateau/NOTICE.md` に記載する港区2025の固定タイル。元のgml_id、座標変換、個別高さ移動はgeoreference.jsonに記録する。全体に一括MIT/CC BYを適用しない。

`facade.py`は旧プロジェクトの`work/interior_walk/glass_return.py`と`work/landmark_rebuild/build.py`から形状生成部分を切り出したもの。実行時の旧blend、profiles.json、ASTによるコード読込、映画用カメラ操作は除外した。旧コードの調査対象hashは調査記録に固定されている。現在の限定MIT grantをこれらの旧コードに拡張するものではない。

頂部と材質には既存の`mori_crown_v2.py`、`mori_facade_v2.py`、`mori_crown_material.py`を使用する。低層部の隣接面検証は`mori_podium_v3.py`。これらは現在の限定MIT grantの対象外。今回の追加ファイルについても、別途明示するまで包括的な許諾を表示しない。公開repositoryで閲覧できることと、第三者が自由に再配布できることは別。

入口・テラス・広場の対象生成関数はroot LICENSE.mdの指定版MIT grantを保持する。広場6部品のCC BY 4.0は詳細タワー全体・入口・テラス全体への許諾ではない。モデルの公開配布は対象部品ごとの条件確定後に行う。今回のコード変更はモデルや第三者TextureをGitへ同梱しない。

外観の参考はPelli Clarke & Partnersの麻布台ヒルズ公式プロジェクト写真、森ビル公式施設案内・フロアマップ、日本設計のプロジェクト資料。リンクは既存patches/mori-podium-repair-v3.jsonに保持している。参考写真をTextureとして取り込まない。頂部高さ、コース、ガラス値、植栽、配置、材質は推定を含む。公式の建物モデル・測量成果・実物と完全一致するモデルを名乗らない。

旧推定値に基づく床・天井・屋根の最小形状を含む。家具・屋上設備、旧道路端の修復、東京タワー本体は今回の生成対象外。旧承認済みシーンとの画面一致は保証しない。

# 資料索引と建物モデルの統合確認

資料の地物IDから目的の建物だけを選び、隣の建物を巻き込まず外形・UVを保ったまま次の街制作へ進めるようになった。

## 公開PRの分離と実行時の依存

main宛の建物PRは、制作と追加検査の担当差分だけを取り込む。`scripts/plateau_evidence.py`、`tests/test_plateau_evidence.py`、資料索引の文書更新は別担当の資料PRへ分離しており、本PRには含まない。

建物生成runnerと建物のテストは索引コードに依存しない。以下の索引から選択する手順だけは、別途資料PRのCLIで作ったJSONを `--index` へ渡す必要がある。既存の索引JSONを読み取るvalidator自体は、このPRだけで実行できる。資料PRは公開準備中で、公開後にPR間のリンクを付ける。

資料索引を除いたmainベースの公開用構成でも241テスト中234成功・任意依存7件省略、compileall成功。下の249テストは資料索引も含めた統合検証時の履歴として区別する。モデル生成コードはその検証版から変更していない。[公開画像と出典](../renders/previews/data221-af7335da-topology/README.md)。

## 統合した版

専用branch `codex/data221-af7335da-integration-20261002` に、mainの指定版 `234b163210ac19d61f33e86b6920b8b26f9d453a`、その直上の資料索引 `7a0ef42`、モデル制作 `c3dba225450ed662434e7e83a39e0c84dd82561d` を組み合わせた。制作commitのcherry-pick後は `ed7043ce5e1e18063ce9f80f2e507f3760395c5a`。競合0件。元branch・commit・通常checkout・通常登録は保全した。これは公開前のローカル統合検証記録である。

## 実際に確認した導線

1. 統合版の `scripts/plateau_evidence.py --check-doc --feature bldg_af7335da-7542-44dd-964d-8cccd2b046ff --inputs LOCAL_INPUTS --output data/local/integration-index-feature.json` を実行。24件の台帳・固定入力整合と対象1件の取得を確認した。
2. [制作runner](../scripts/review_data221_af7335da.py)を統合版から新しい出力先 `data/local/af7335da-integrated-01` へ実行。PR #47の保存済みcityと同じ固定PLATEAU入力を使い、街全体の候補、対象ライブラリ、4視点×2状態を再生成した。
3. [追加validator](../scripts/validate_data221_af7335da_integration.py)が索引の `scene_lookup.mori_after_property=gml_id` と値を使い、生成済み近隣モデルから一致する1オブジェクトを選択。選択中のモデルを `selected-neighborhood.blend` に保存した。
4. 別Blender processでそのファイルを開き直し、active objectと唯一のselected objectが完全な対象IDであることを確認した。scene内の2 mesh objectは、独立対象1地物と残り22地物のaggregate。通常BlenderへのUI操作・登録はしていない。

追加検証のコマンド（Blender 4.5.1、`LOCAL_ORIGINAL_REVIEW` は制作commitの既存run）：

```powershell
& $blender --background --factory-startup --threads 2 --python-exit-code 1 `
  --python scripts/validate_data221_af7335da_integration.py -- `
  --index data/local/integration-index-feature.json `
  --review data/local/af7335da-integrated-01 --reference LOCAL_ORIGINAL_REVIEW --phase check

& $blender --background --factory-startup --threads 2 --python-exit-code 1 `
  --python scripts/validate_data221_af7335da_integration.py -- `
  --index data/local/integration-index-feature.json `
  --review data/local/af7335da-integrated-01 --reference LOCAL_ORIGINAL_REVIEW --phase reopen
```

## 形状・再現性の結果

| 検査 | 結果 |
|---|---|
| 頂点 / 面 / 辺 | 235 / 466 / 699 |
| 重複する幾何面 | 0 |
| 境界辺 / 非多様体辺 / 辺の向き不整合 | 0 / 0 / 0 |
| 頂点リンク | 235頂点すべて単一閉ループ、非多様体リンク0 |
| 接続成分 / Euler標数 | 1 / 2 |
| 面法線と元面の向き | 466面照合、最大差0.00001168°（数値精度範囲） |
| 元shape・UV・材質割当・材質定義・batch・flat shading | 一致 |
| 統合前後の形状測定・保存後city検証 | 一致 |
| 統合前後の8枚の描画 | デコード後の全画素hash一致 |
| テスト | 249件中242成功、任意依存7件省略、失敗0 |

辺・頂点・向きを含む接続条件を確認した。**幾何学的な自己交差は調べていないため、watertightな実体・衝突形状として認定しない。** 元の位置と面は変えていない。

`.blend` の独立保存結果はバイト単位では一致しない。これは形状再現性と分けて記録し、同じ入力・展開した面/UV/材質・街のfingerprint・画素の一致で再現を確認した。worktree間の改行コード差を正規化すると、制作に使ったコードも一致した。

[機械可読の統合証跡](data221-af7335da-integration-evidence.json)に入力、コード、出力、追加検証、索引、画像hashを保持。ローカル成果は `data/local/af7335da-integrated-01/review.html`、`after.blend`、`target.blend`、`selected-neighborhood.blend`。Blenderの既存extension cache警告は残ったが、生成・再open・描画はすべてexit 0。

## 次の見た目制作候補

塔身の垂直面で、高さ30m以上・隣接面法線の差0.1〜30°という条件に14辺が一致し、角度範囲は0.166〜26.257°だった。現在は全三角形がflat shadingである。**塔身の緩い折れ目だけを対象に、法線スムージングの有無を同条件で比較する**ことを次候補とする。元頂点とUV、屋根・低層部・鋭い稜線を固定して、窓や設備を足さずに見た目を検討できる。

これは入力にある輪郭の陰影を扱う比較案で、現実の外壁が曲面であるとの同定ではない。14辺を一括で変更すると角が丸く見えすぎる可能性があるため、部位別の比較画像を見て採否を決める。今回は法線変更を実施していない。建物名と216mの高さ属性の解釈は引き続き未確定であり、形状・縮尺変更には使わない。

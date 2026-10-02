# data221 batch 15：個別編集できる建物メッシュ

[公開用の代表Before/After](../renders/previews/data221-af7335da-topology/README.md)で、外観を保ったまま対象だけを編集可能にした結果を確認できる。今回のmain宛PRは建物担当の変更だけを含み、資料索引と不採用の法線調整は含めない。

対象は `bldg_af7335da-7542-44dd-964d-8cccd2b046ff`。固定PLATEAU入力の名称はnullのため、建物名は推定しない。2025港区入力のLOD2.2、XY外接範囲は東西−513.696〜−405.517m、南北353.652〜454.443m、旧表示用高さは0.32〜236.333m。[入力の座標・根拠](plateau-data221.md)を参照。

同じ固定b3dmのbatch tableから公式建物ID `13103-bldg-7517` と `bldg:measuredHeight=216m` を確認した。高さ属性とジオメトリ全体の約236.01mの上下幅は意味が異なる可能性があり、その関係は未確認。216mへ縮めたり、基準高さを推定で置き換えたりしない。

元のcityでは23地物が `PLATEAU_data221` に結合され、対象の466三角形も各面ごとに頂点が分離していた。対象を地物ID付きの1オブジェクトへ分け、**完全に同じ座標の頂点だけ**を共有化する。元の466面、面の向き、UV、材質スロット、フラットシェーディング、座標を保持する。建物を面のつながりから選択・編集できる状態にする変更であり、現地形状の修正や詳細化は主張しない。

| 対象の実メッシュ | Before | After |
|---|---:|---:|
| 頂点 | 1,398 | 235 |
| 三角形 | 466 | 466 |
| 接続成分 | 466 | 1 |
| 境界辺 | 1,398 | 0 |
| 向き不整合の辺 | 0 | 0 |
| 面積 | 58,658.822218m² | 58,658.822218m² |
| 符号付き体積 | 566,337.148369m³ | 566,337.148369m³ |

残る22地物の2,694面は、頂点位置・面順序・UV・材質・batch IDを保持する。頂点インデックスの振り直しはある。対象の頂点削減は1,163（83.2%）。元PLATEAUとの最大座標差0.000027711mは既存cityのfloat32丸めであり、今回の座標移動は0m。

## 入力と変更範囲

- コード起点：PR #47取り込み後 `234b163210ac19d61f33e86b6920b8b26f9d453a`。
- city入力：PR #47の保存済み `after.blend`、SHA-256 `2a6f63658722beecdb8af2158baed62c044f33a22084df0d227c70c67332ae5b`。
- 元資料：既存の `data221.b3dm`（SHA-256 `dc8c7539b2bb22d8c6659689c37aafa53b4896650bbd6bcfe7f791ab8b1a38d2`）と `tileset.json`（SHA-256 `edec4c24d137eaf08a8525cecea505a3f21a30823b9ef4fb530e10774cea1323`）。取得は行わない。
- モデル変更：`PLATEAU_data221` からbatch 15を取り出し、同じcollections内へ完全な地物IDを名前・`gml_id`属性として持つオブジェクトを追加する。森JP、園路、道路、他タイルは変更しない。
- 共通runner・台帳・通常workspace登録を変更しない。親レビュー前のローカル候補であり、採用基準の更新ではない。

## 再現

Blender 4.5.1と付属Pythonで、許諾済みの保存入力を指定する。出力先は新しいディレクトリに限り、既存出力と二重追加は拒否する。

```powershell
& $python -B scripts/review_data221_af7335da.py `
  --blender $blender `
  --input 'LOCAL_PR47_AFTER.blend' `
  --input-sha256 2a6f63658722beecdb8af2158baed62c044f33a22084df0d227c70c67332ae5b `
  --inputs 'LOCAL_EXISTING_PLATEAU_INPUTS' `
  --output data/local/af7335da-review-new
```

`$python` はBlender付属Python、`$blender` はBlender 4.5.1の実行ファイルを指定する。`after.blend` は街全体の候補。`target.blend` は対象オブジェクトをAppendできる小さなBlenderライブラリで、街全体の登録用ファイルではない。`before-neighborhood.blend` / `after-neighborhood.blend` は同じ23地物の比較用ライブラリ。`review.html` と4視点×Before/AfterのPNGを出力する。モデル・入力は `data/local/` に保持し、代表画像2組だけを出典付きで公開する。

## 検証と限界

2026-10-02の実行は成功。[測定・hash・検証記録](data221-af7335da-topology-evidence.json)。対象外3,307 object、383画像、既存カメラ・照明、残る22地物の展開面データが一致した。4視点のBefore/Afterはデコード後の画素hashも全て一致し、全高・屋根・低層部の表示を目視確認した。専用6テスト成功、全体238テスト中231成功・任意依存による7件省略。input SHA-256も実行前後で一致した。

ローカル成果：`data/local/af7335da-review-01/review.html`、`after.blend`（約559MB）、`target.blend`（約759KB）。Blender終了時に既存extension cacheへの書込み警告が出たが、4工程ともexit 0、保存後検証・画像出力は成功。通常のBlender設定・登録は変更していない。

保存後の別Blender processで、元cityの対象外object・画像資産・カメラ・照明、残る22地物の展開面データ、対象の元資料一致と閉じた接続を照合する。全工程の入力・コード・モデルのhashを `run.json`、形状測定を `production.json`、保存後結果を `validation.json` に残す。比較は東・西の全高、屋根、低層部の4視点。CPU 2 threads、Cycles 16 samples、seed 0、800×800、照明・カメラを揃える。

画像は同じdata221の23地物に限る軽量表示。道路・地形・森JP詳細版を含む全都市レンダーではない。外観を保つため、既存の合成ファサード材質と旧表示用の地物別高さ合わせを引き継ぐ。実測標高・現在の外装・歩行接続・自己交差・衝突用途の保証は含まない。一般の全Blender機能の同値性検証ではなく、既存review harnessのfingerprint範囲を引き継ぐ。

この作業は新しい素材ライセンスや配布権を追加しない。[PLATEAU入力の出典・条件](../starter/plateau/NOTICE.md)と既存cityの扱いを保持する。次は親担当がこの候補と並行制作を統合レビューし、画像と変更範囲を確認してから公開可否を判断する。窓や設備などの実物ディテールを増やす場合は、対象IDと対応する許諾済み資料を先に追加する。

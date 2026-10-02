# data221 batch 0：外観を保持した個別編集化

対象は `bldg_0551e688-a2a3-498e-ad2f-09ed3aca361c`、固定PLATEAU入力のbatch 0、946三角形。名称を推定せず、[既存資料索引](plateau-data221.md)と入力の完全な地物IDで指定した。2026-10-02に実モデルを修正し、ローカル候補として保存した。現実の外装や装飾を追加する作業ではない。

元cityでは対象を含む22地物が `PLATEAU_data221` に結合され、対象の946面は面ごとに頂点が分離していた。完全に同じ座標の頂点だけを共有し、対象を独立した1オブジェクトへ分けた。座標移動・面削除・法線再計算・smooth化を行わず、面の順序と向き、UV、active/render/clone UV設定、材質スロットと定義、配置を保持する。

| 実メッシュ | Before | After |
|---|---:|---:|
| 頂点 | 2,838 | 475 |
| 三角形 | 946 | 946 |
| 接続成分 | 946 | 1 |
| 境界辺 | 2,838 | 0 |
| 重複する幾何面 | 0 | 0 |
| 面積 | 5,559.823073m² | 5,559.823073m² |
| 符号付き体積 | 18,505.892316m³ | 18,505.892316m³ |

修正後は非多様体辺0、向き不整合辺0、475頂点のlink異常0、Euler特性2。今回の固定対象で実測した単一閉殻の条件であり、すべての建物が単一殻であるという前提ではない。幾何的な自己交差や物理衝突用solidの保証はしない。

## 入力と前成果の保持

- コード起点：`05026ec9de08b25e15e8e77c2ad2e2a43a1b5f6d`。リモートmainの後続 `29157afbab0ce05e62d065b3535e577230b7583a` はPR #50のviewer変更のみと確認。今回の建物コードとは重ならない。
- 制作コード：`417103f`。実行ファイルのSHA-256と完全なcommitは[機械可読証跡](data221-0551e688-evidence.json)にも記録する。
- city入力：先行建物af7335daの統合検証済み `after.blend`。SHA-256 `09977e34f02c02a7e24448767874294e0f7c09e3bbaf40b5630ea1dea8965216` を固定。旧成果のファイルは上書きしない。
- `data221.b3dm`：`dc8c7539b2bb22d8c6659689c37aafa53b4896650bbd6bcfe7f791ab8b1a38d2`。`tileset.json`：`edec4c24d137eaf08a8525cecea505a3f21a30823b9ef4fb530e10774cea1323`。既存入力を読み、両ファイルのサイズ・hashを確認。
- 公式入力と旧cityの最大座標差は0.000015242209m。これは旧cityのfloat32丸めに相当する照合差であり、今回の編集による座標移動は0m。
- 元の21地物・1,748面をaggregateに保持。既編集 `bldg_af7335da-7542-44dd-964d-8cccd2b046ff` を含む対象外3,308オブジェクト、383画像、既存カメラ・照明は保存後比較で一致。
- 通常checkout、workspace登録、先行建物・タワー・街路・樹木・viewerのファイルを変更しない。共有Gitには専用branch/worktreeとローカルcommitを追加し、remote-tracking mainを取得した。push・PR・mergeは行っていない。

## 再現と成果物

Blender 4.5.1と付属Pythonを指定する。出力先は未作成ディレクトリに限る。入力hash不一致、対象がすでに存在する場合、対象外変更、画像不足・画像差異を拒否する。

```powershell
& $python -B scripts/review_data221_0551e688.py `
  --blender $blender `
  --input 'LOCAL_AF7335DA_INTEGRATED_AFTER.blend' `
  --inputs 'LOCAL_PINNED_PLATEAU_INPUTS' `
  --output data/local/0551e688-review-new
```

最終成果は専用worktree内の `data/local/0551e688-review-02/` に置く。

- `after.blend`：先行成果を含む街全体の候補。対象を選択状態で保存。
- `edit-neighborhood.blend`：対象とdata221の周辺地物を含む小型編集scene。対象IDを持つ1オブジェクトがactive/selected。
- `target.blend`：対象だけをAppendできるライブラリ。通常sceneの代替ではない。
- `review.html`：4視点のBefore/After、検査JSONへのリンク。
- `production.json` / `validation.json` / `edit-reopen.json` / `run.json`：形状、街全体の再open、編集scene・単体ライブラリの再open、コードと入出力hash。

最初の `0551e688-review-01` も上書きせず保持した。最終版ではAstraによる独立レビューを受け、画像の4視点ID・件数確認、編集scene全3メッシュと単体ライブラリの保存後比較を追加した。モデルの形状・描画条件は変更していない。

## 検証と画像確認

専用関連14テスト成功。全254テスト中247成功、任意依存7件省略。保存後の街全体を別Blender processで再openし、対象の形状・UV・材質・batchデータ、対象外の指紋、カメラ・照明、画像資産を照合する。小型編集sceneの全メッシュと単体ライブラリも別processで再open検査する。

南・北・屋根の対象単体3視点と、data221周辺23地物を含むcontext 1視点を使用。800×800、CPU 2 threads、Cycles 16 samples、seed 0、固定カメラ・照明・表示設定でBefore/Afterを描画。4組すべてのデコード画素が一致し、8画像を目視確認した。屋根の曲線状輪郭、外壁、張り出し部分、隣接する先行建物に欠落やずれは見られない。既存テクスチャのぼけや合成外壁表現は保持した。

実行時に並行処理を確認。こちらは軽量な建物抽出だけを描画し、全都市レンダーを実施しない。観測時CPU58%、GPU2〜7%、空き物理メモリ約22GB。Blenderの既存extension cache書込み警告はあるが、モデル生成・検証・描画の成功とは区別してログに保持する。

これは既存review harnessのfingerprint範囲での保全検査であり、全RNA・modifier・animation・node group等の一般的な同値性を保証しない。道路・地形との接続、実測高さ、現在の外観の正確さ、別PCでの検証は今回の範囲外。[固定入力の出典・条件](../starter/plateau/NOTICE.md)を引き継ぎ、新しい配布権を主張しない。モデル・テクスチャ・比較画像はローカルに保持する。

## 次の独立候補

`bldg_5dab31bf-48b2-4de9-8f4f-3ff552347f28`（この版のbatch 6、212面）を候補として返す。現入力の読み取り検査では各面分離の636頂点を完全同座標で共有すると108頂点、1成分、境界辺・向き不整合・重複面・頂点link異常が0。今回のモデル変更対象には含めず、予約・制作は次の独立タスクで判断する。batch 8・13には共有化後の非多様体箇所、batch 17には10成分を観測したため、今回の単一殻の受入条件を横展開しない。

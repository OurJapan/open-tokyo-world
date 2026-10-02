# data221 batch 0：外観を保持した個別編集化

対象は `bldg_0551e688-a2a3-498e-ad2f-09ed3aca361c`、固定PLATEAU入力のbatch 0、946三角形。名称を推定せず、[既存資料索引](plateau-data221.md)と入力の完全な地物IDで指定した。完成済みの個別編集化をmain `3b1eb5f6c10ca9c0ebb072348faea4981985439e` へ統合し、再生成・保存後再読込・同条件4視点を再検証した。[比較画像8枚](../renders/previews/data221-0551e688/README.md)と[今回の検証証跡](data221-0551e688-main-validation.json)をDraft PR用に公開する。現実の外装や装飾を追加する作業ではない。

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

修正後は非多様体辺0、向き不整合辺0、475頂点のlink異常0、Euler特性2。今回の固定メッシュ上で計測した単一閉殻の条件であり、すべての建物が単一殻であるという前提ではない。幾何的な自己交差や物理衝突用solidの保証はしない。

## 入力と前成果の保持

- 制作起点：`05026ec9de08b25e15e8e77c2ad2e2a43a1b5f6d`、制作コード `417103feb85dbe3ac67ce5c3f5afc8ed593b5a58`、旧証跡 `25e8c71bcd2af58a69791bbe8d6c1ef2f3262ba4`。当時の[ローカル検証記録](data221-0551e688-evidence.json)は履歴として保持する。
- 統合先：`3b1eb5f6c10ca9c0ebb072348faea4981985439e`。後続PR #50（viewer）・#51（植栽）と実行コード・依存10ファイルに重複変更なし。競合なしで2コミットを移し、`d4df2e65828ad2909af464e44485f83f7c4ef0ab` のコードで再実行。PR headとの対応は実行ファイルhashでも確認する。
- city入力：先行建物af7335daの統合検証済み `after.blend`。SHA-256 `09977e34f02c02a7e24448767874294e0f7c09e3bbaf40b5630ea1dea8965216` を固定。旧成果のファイルは上書きしない。
- `data221.b3dm`：`dc8c7539b2bb22d8c6659689c37aafa53b4896650bbd6bcfe7f791ab8b1a38d2`。`tileset.json`：`edec4c24d137eaf08a8525cecea505a3f21a30823b9ef4fb530e10774cea1323`。既存入力を読み、両ファイルのサイズ・hashを確認。
- 公式入力と旧cityの最大座標差は0.000015242209m。これは旧cityのfloat32丸めに相当する照合差であり、今回の編集による座標移動は0m。
- 元の21地物・1,748面をaggregateに保持。既編集 `bldg_af7335da-7542-44dd-964d-8cccd2b046ff` を含む対象外3,308オブジェクト、383画像、既存カメラ・照明は保存後比較で一致。
- 原本checkoutと引継ぎworktreeは保護。Git管理領域も独立コピーした専用worktreeで作業し、引継ぎの5つのblendのhash不変を照合した。通常workspace登録・共通city基準は更新しない。今回の公開範囲はユーザーが明示承認したコード・検証資料・小型PNGのみ。マージは承認範囲に含まれない。
- city入力は先行建物の固定候補のまま。PR #51の植栽を加えた新しい合成cityを作ったとは扱わない。mainとのコード整合・既存周辺保持と、候補同士の完全合成は別の検証である。

## 再現と成果物

Blender 4.5.1と付属Pythonを指定する。出力先は未作成ディレクトリに限る。入力hash不一致、対象がすでに存在する場合、対象外変更、画像不足・画像差異を拒否する。

```powershell
& $python -B scripts/review_data221_0551e688.py `
  --blender $blender `
  --input 'LOCAL_AF7335DA_INTEGRATED_AFTER.blend' `
  --inputs 'LOCAL_PINNED_PLATEAU_INPUTS' `
  --output data/local/0551e688-review-new
```

今回のローカル成果は専用worktree内の `data/local/0551e688-main-review-01/` に置く。

- `after.blend`：先行成果を含む街全体の候補。対象を選択状態で保存。
- `edit-neighborhood.blend`：対象とdata221の周辺地物を含む小型編集scene。対象IDを持つ1オブジェクトがactive/selected。
- `target.blend`：対象だけをAppendできるライブラリ。通常sceneの代替ではない。
- `review.html`：4視点のBefore/After、検査JSONへのリンク。
- `production.json` / `validation.json` / `edit-reopen.json` / `run.json`：形状、街全体の再open、編集scene・単体ライブラリの再open、コードと入出力hash。

引継ぎ `0551e688-review-02` と今回の `production.json`、`validation.json`、`edit-reopen.json` の内容は完全一致。全4視点のデコード画素hashも旧成果と一致した。blendは再保存でbyte hashが変わるため、内容の検査とファイルhashを区別して記録する。

## 検証と画像確認

最新main上の全280テスト中273成功、任意依存7件省略（Shapely 2件、写真推定依存5件）。`compileall` と差分検査も成功。生成・都市再読込・Before描画・After描画・編集scene再読込の5プロセスが終了0。保存後の街全体を別Blender processで再openし、対象の形状・UV・材質・batchデータ、対象外の指紋、カメラ・照明、画像資産を照合した。小型編集sceneの全3メッシュと単体ライブラリも再open検査した。

南・北・屋根の対象単体3視点と、data221周辺23地物を含むcontext 1視点を使用。800×800、CPU 2 threads、Cycles 16 samples、seed 0、固定カメラ・照明・表示設定でBefore/Afterを描画。4組すべてのデコード画素が一致し、8画像を目視確認した。屋根の曲線状輪郭、外壁、張り出し部分、隣接する先行建物に欠落やずれは見られない。既存テクスチャのぼけや合成外壁表現は保持した。

軽量な建物抽出を描画し、全都市レンダーは実施していない。Blenderの既存extension cache書込み警告が描画・再読込ログにあるが、5プロセスすべて終了0。完全なログと大型成果物はignoredなローカル出力へ保持する。

これは既存review harnessのfingerprint範囲での保全検査であり、全RNA・modifier・animation・node group等の一般的な同値性を保証しない。道路・地形との接続、実測高さ、現在の外観の正確さ、自己交差、別PCでの検証は今回の範囲外。[固定入力の出典・条件](../starter/plateau/NOTICE.md)を引き継ぎ、新しい配布権を主張しない。モデル・テクスチャ・元タイルは公開しない。PNGは今回承認されたレビュー用証拠としてのみ公開し、素材の再配布許諾を追加しない。

## 次の独立候補

`bldg_5dab31bf-48b2-4de9-8f4f-3ff552347f28`（この版のbatch 6、212面）を候補として返す。現入力の読み取り検査では各面分離の636頂点を完全同座標で共有すると108頂点、1成分、境界辺・向き不整合・重複面・頂点link異常が0。今回のモデル変更対象には含めず、予約・制作は次の独立タスクで判断する。batch 8・13には共有化後の非多様体箇所、batch 17には10成分を観測したため、今回の単一殻の受入条件を横展開しない。

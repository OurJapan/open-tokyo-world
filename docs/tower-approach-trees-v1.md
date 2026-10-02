# 東京タワー北東アプローチの並木と箱形植樹枡

旧cityで親collectionの描画設定により隠れている街路樹から、東京タワー北東側のイチョウ8本を独立collectionへ表示し、土面と縁枠を制作しました。既存の推定XY配置を保持し、土面を舗装より高く出して根元を接地しています。編集画面の二重表示を防ぐため、対象の元16部品だけを `hide_viewport=True` にします。これは人間の採用判断を待つ街制作候補です。

実制作commit `b92061b5` と元モデルを保持し、専用branchでmain `234b163210ac19d61f33e86b6920b8b26f9d453a` とPR #47の保存済み園路候補へ統合しました。[同条件の代表画像](../renders/previews/tower-approach-trees-v1/README.md)と[保存後の検証証跡](tower-approach-trees-v1-validation.json)を公開レビュー用に添えています。

## 制作内容と根拠

地物IDは `otw:jp:tokyo:minato:tokyo-tower:northeast-approach-trees-v1`、collectionは `OTW Tokyo Tower northeast approach / trees v1` です。[固定設定](../areas/tokyo-tower/approach-trees-v1.json)に元オブジェクトの変換、8本のID、表示倍率、寸法、4つのカメラを保持します。

| 内容 | 根拠と精度 |
|---|---|
| イチョウ3種類の幹・樹冠6メッシュ、4材質 | [既存のCC BY 4.0許諾記録](../assets/procedural-components/provenance.json)の形状hash・材質signatureに一致。作者表示はark4ez / OurJapan |
| 元配置158、160、164、166、168、170、172、174 | 既存のOSM由来の説明用配置から選択。樹種・本数・植栽位置の現地確認は未実施 |
| 中心XY：X −26.211〜69.435m、Y 28.867〜77.443m | 元のモデル座標を保持。測量された樹木座標とは扱わない |
| 外幅1.20m、内幅1.04mの箱形植樹枡 | 独自の制作提案。現地の植樹枡形状を同定したものではない |
| 土面Z=0.68m、縁上端Z=0.72m、底面Z=0m | 既存モデルの地盤Z=0m・舗装Z=0.46mに合わせた仮の高さ。舗装上に土面22cm、縁26cmが出る |
| 配置166の表示幅のみ95% | 幹・樹冠のローカルXY倍率を0.95にして、保存された壁との面交差を解消。高さ倍率と中心XYは保持 |

植樹枡の下部は地盤まで伸ばす挿入表現で、Z=0.46m以下では既存舗装の一部と重なります。土面と上縁は既存舗装より上にあり、土面の視認と幹の接地を検査しました。土塊・枠全体に対する歩道の掘削や交通用衝突形状は未制作です。

初期候補の土面Z=0.44mは舗装に隠れ、幹と舗装の面交差もあったため、今回の高さへ変更しました。配置166の樹冠には壁との交差3組があり、幅の調整後に0組となりました。別の元配置162はタワー鉄骨と交差するため追加対象に含めていません。こうした配置判断はモデル内の検査に基づき、現地形状の確認に置き換えるものではありません。

## 再生成と統合

大型city、増分blend、固定道路入力、完全なログは、正当な提供元から受け取るローカル入力です。通常workspace登録と通常Blender設定は更新しません。元cityの配布権を付与するPRではありません。

```text
PYTHON scripts/tower_approach.py --input RECEIVED_ACCEPTED_CITY --blender BLENDER --output data/local/approach-new --device OPTIX --width 960 --height 540 --samples 16
PYTHON scripts/tower_approach_integration.py --input RECEIVED_PR47_CITY --delta RECEIVED_REVIEWED_DELTA --blender BLENDER --output data/local/approach-integration-new
```

最初のrunnerは[入口接続採用版](../manifests/mori-plaza-connection-accepted.json)559,040,261 bytes、SHA-256 `9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4`を要求します。統合runnerはPR #47候補のSHA-256 `2a6f63658722beecdb8af2158baed62c044f33a22084df0d227c70c67332ae5b`と、記録した増分ライブラリのhashを確認します。再保存されたblendのbyte hashは変わり得るため、再生成したライブラリには確認済みhashを `--delta-sha256` で明示します。形状・材質・表示変換・追加範囲・画像／Text／外部リンク不在の検査は続けて適用されます。

最終候補はローカル `data/local/tower-approach-pr47-review-03/` の `after.blend`、`approach-additions.blend`、`review.html` と各phaseのJSON/logです。増分は18オブジェクト、8メッシュ、4材質で、cityの画像・建物・カメラ・照明・埋め込みTextを含みません。collection属性 `otw_source_viewport_suppression` が元16部品の名前を保持します。統合時には追加prototypeとshaderを検査して既存データを再利用し、材質名のsuffix増殖を防ぎます。同じcollectionや対象名がある場合は二重適用を拒否します。

園路の追加検証は既存validatorを変更せず、保存済みsceneから全道路配列・ray・seam・patch状態を再取得します。

```text
PYTHON scripts/tower_approach_west_recheck.py --blender BLENDER --before RECEIVED_PR47_BEFORE --after LOCAL_INTEGRATED_CITY --after-sha256 CHECKED_CITY_SHA --reference RECEIVED_PR47_AUDIT --seam-plan RECEIVED_PINNED_PLAN --output data/local/approach-west-replay-new
```

## 検証範囲と採用判断

Blender 4.5.1 LTSで保存後の街と増分を別プロセスで再読込しました。PR #47候補の既存3,308オブジェクトの形状・材質・変換・描画設定・所属・記録対象属性を保全し、元16部品の編集表示抑制だけを許可します。他3,292オブジェクト、既存17collection、383画像の検査記録、記録対象scene設定が一致しました。追加は18オブジェクトです。既存36警告に増加はありません。

根元と土面、隣接舗装、閉じた植樹枡の寸法・外向き体積、車道／タワー基礎への投影面積を検査しました。投影重複は0㎡です。幹・樹冠とタワー鉄骨／基礎、対象道路および候補領域に達するPLATEAU・旧roof/wallの保存された三角形面との交差は0組でした。建物の植樹枡内検査は各5点です。これは実体の包含、全modifier評価、地形掘削や交通用衝突の完成を保証する検査ではありません。

西側園路の3道路メッシュとseamを保全し、採用済み監査に対してbefore／afterの道路配列と各5,517ray、seam形状・patch状態の一致を検査しました。GEOSの面積・閉形状結果は、その入力が同一の場合に限って採用済み結果を再利用しています。園路のvalidator・patch・testsは変更していません。Astra担当の固定建物ライブラリも軽量な別読込で照合し、名前空間と全樹冠を囲むXY範囲に重なりがないことを確認しました。建物込みの街全体再生成は行っていません。

4つの植栽視点と2つの園路視点を、Cycles OptiX、960×540、16 samples、seed 0、frame 1、同じカメラ・照明・色管理で描画し、12枚を目視確認しました。関連26テスト、portable全体テスト、構文・差分検査の結果は検証JSONに記録します。保存済み候補への再appendは終了1で拒否し、候補hashは不変でした。

現地の位置・樹種・季節・道路高度、歩行者の連続通行幅、完全な衝突／modifier／animation、別PCでの性能は未確認です。人間が画像と暫定表現を確認して採否を判断し、次に植樹枡周囲の通行幅と下部の歩道接続表現を詰めます。公開pushと画像付きDraft PRは2026-10-02の依頼で許可されました。採用・共通登録更新・mergeは別の判断です。

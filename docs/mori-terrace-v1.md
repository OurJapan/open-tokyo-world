# 森JPタワー：広場側の一段の植栽・手すり

Issue #5。main `d2235f2`（PR #2・#4のmerge後）から開始。人間が承認した建物に、北東側の一つの屋根テラスを追加する画像レビュー候補です。

## 根拠と推定

確認日：2026-09-07。日本設計の[プロジェクト紹介](https://www.nihonsekkei.co.jp/projects/19811/)にある、[広場を見下ろす写真](https://www.nihonsekkei.co.jp/wp-content/uploads/2025/03/1600x1066_092_71A3817.jpg)では、画面左の低層部屋上に植栽と茶系の縦桟手すりが見えます。[広場全景](https://www.nihonsekkei.co.jp/wp-content/uploads/2025/05/b42c9dc63b47229435cdf2f81d78a72c.jpg)と塔・広場・低層棟の相対配置を照合しました。写真はリンクのみで、モデルのTextureには使用していません。撮影日・個別写真の再配布許諾は不明です。

資料から確認できるのは、植栽・縦桟手すりの存在と見える傾向です。写真の棟とsource屋根の対応は相対配置による推定（確度：中）、植栽の本数・樹種・寸法・手すりの設置線は推定（確度：低）。測量図との照合は未実施です。

対象はsource batch 5の北東張り出し、屋根高さ約20.08m。登録原点はlegacy local `(-402.80, 282.29)`、長手軸は `(2,-1)/sqrt(5)`。Source由来の実体parapetは保持し、そのテラス内側に高さ1.2mの手すりを置いています。実体parapetを縦桟へ置換したものではないため、外側からは一部が隠れます。4本の樹木、L字の低木帯と植栽基盤を原創の手続き形状で生成。樹冠は軽量な代理形状です。新しい発光材質はありません。

## 変更範囲

既存の非表示slot `Mori JP podium / soil, leaf, wood, gasket` の4つのみを置換・表示します。対象地物ID、変更前mesh hash、非表示状態、identity transform、単独mesh所有を検査します。毎回固定入力から実行し、重複追加を防ぎます。建物・旧parapet・入口は編集しません。

## 固定入力と再実行

今回から採用済みblendを別の入力lockとして明示します。旧legacy lockやfeaturesは変更しません。

- 入力：ローカルの `accepted-2026-09-07.blend`、553280443 bytes。
- SHA-256：`77752f9009a0f3a1979734e3374de50d933253a5408c99f38297765548969179`。
- 来歴：`docs/mori-reviewed-baseline.json` と `docs/mori-review-acceptance.md`。モデルcode commit `e684614`。
- Lock：`manifests/mori-accepted-2026-09-07.json`。
- Mapping：`areas/tokyo-tower/mori-accepted-features.json`。5つの空mesh例外は承認済み入力に固定し直し、Beforeの別process検証で再確認します。追加対象は例外に含めません。
- Patch：`patches/mori-terrace-v1.json`。

```sh
python -m unittest discover -s tests
python scripts/review.py --blender BLENDER --input ACCEPTED_BLEND --lock manifests/mori-accepted-2026-09-07.json --features areas/tokyo-tower/mori-accepted-features.json --cameras areas/tokyo-tower/mori-terrace-cameras.json --patch patches/mori-terrace-v1.json --output NEW_RUN --device OPTIX --width 960 --height 540 --samples 24 --timeout 1200
```

この増分patchに `--geometry-source` は不要です。採用済みblendを持たない参加者は、旧原本と固定source archiveから前PRの累積patchで再構築する必要があります。Blenderの保存結果はbyte一致を保証しないため、再構築ファイルをこのlockに無条件で通すことはできません。独立環境の再現と資産配布の課題は未解決です。

## レビュー

6視点を同じカメラ・照明・seed・24 samplesで新規生成します。主視点はテラス俯瞰と内側、補助視点は入口・全景・頂部・前回欠落のあった低層部です。人間の受入は未完了です。

追加形状の閉じた辺、有限座標、footprint、再生成一致を契約テストで確認します。全都市のwatertightness、法規適合や地理的正確さを保証する検査ではありません。保存後の実行結果・形状量・処理時間は `mori-terrace-v1-validation.json` に記録します。

追加形状の保存後検査は、別processで `BLENDER --factory-startup --background --disable-autoexec --python-exit-code 1 --python scripts/validate_mori_terrace.py -- --candidate NEW_RUN/after.blend --output NEW_AUDIT.json` を実行します。出力は新しいファイル名を指定してください。

実行結果：24契約テスト・Blender 2ケース・6視点12画像が成功。総object数は3,299を保持し、総polygon増分は133,398（約0.34%）。隠れていた旧部品を置換するため、追加した可視polygon数151,326とは異なります。

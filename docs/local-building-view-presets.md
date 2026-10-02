# ローカル建物の視点切替

`?local_model=data221-af7335da` で実モデルを確認するとき、全景・北から・東からのボタンで同じ方向に戻せます。既存の全景に加えて二方向を選べるため、外壁と低層部を繰り返し比較できます。

- 選択中の視点は画面の縦横切替やサイズ変更でも維持し、建物全体が収まる距離に調整します。
- ドラッグ・パン・ズームを始めると「自由視点」になり、その後のサイズ変更では手動の位置を維持します。
- 「全景に戻す」で初期の全景と自動フィットに戻ります。慣性が残っていてもプリセットは同じ位置に切り替わります。
- 各ボタンは Tab で移動し、Enter または Space で選べます。選択状態を色・枠と `aria-pressed` で示します。

北・東は既存の `east-up-south` モデル座標に基づく目安です。少し上から建物中心を見る透視投影であり、測量済み方位や正投影の立面図ではありません。既存の地物ID、モデルのメートル尺度、出典、現地標高の未検証表示は保持します。

## 手元で開く

既存の検証済み `manifest.json` と `model.glb` を `data/local/web-exports/data221-af7335da/` に置き、依存関係を用意した状態で実行します。元blendやモデルを編集する必要はありません。

```powershell
Set-Location web/spatial-viewer
node node_modules/vite/bin/vite.js --configLoader native --host 127.0.0.1 --port 5173 --strictPort
```

`http://127.0.0.1:5173/?local_model=data221-af7335da` を開きます。既存の別の出力先を使う場合、起動前に `OTW_LOCAL_REVIEW_DIR` を設定します。指定先はこのworktree内の `data/local/` 配下に限ります。

この画面は開発server限定です。読み込み・ID・hash・形状の検証後に視点操作を表示します。通常の検証モデル画面と本番buildでは表示しません。モデル・テクスチャはGitやbuildへ追加しません。

## 操作と描画の確認

```powershell
Set-Location web/spatial-viewer
node --test tests/*.test.js
$env:BROWSER_CHANNEL = 'msedge'
node tests/local-views-browser.cjs
```

ブラウザ確認は既存のローカル建物を使い、localhost以外へのリクエストを遮断します。960×900、390×900、900×390、320×740のviewport、キーボード、方向と全体の収まり、慣性後の切替、手動操作後のresize、読み込み失敗、通常画面を検査します。出力は既定で `data/local/view-presets/` です。

変更前の画面を記録するときは `LOCAL_VIEWS_BEFORE=1` を指定して基準コード上で確認します。比較時はこの変数を解除し、`LOCAL_VIEWS_BASELINE` に変更前画像のフォルダーを指定すると、全景と通常の検証モデルのcanvas PNGが一致することも確認します。出力先は `LOCAL_VIEWS_OUTPUT` で変更できます。ブラウザ状態の検査用コードはテストの応答にだけ追加し、アプリには含めません。

これはheadlessブラウザのviewport確認で、実機のSafariやタッチ操作の認定ではありません。撮影・オフライン保存などの共通画面は、既存の `tests/field-browser.cjs` と `tests/render-transitions-browser.cjs` で確認します。

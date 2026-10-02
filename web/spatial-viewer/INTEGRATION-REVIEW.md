# PR47後のviewer統合確認

2026-10-02、指定main `234b163210ac19d61f33e86b6920b8b26f9d453a` から独立worktreeを作り、元commit `04402500c8bbb2f55441fa909190d92bf2296e87` を適用した。適用先commitは `b6306bbf552fc21538dcdee4ed80aed74ccb66a9`。元branch/worktreeを保全し、共通checkout、園路patch、生成・検査コード、モデル、Blender登録は変更していない。push/PR/mergeは保留。

PR47の変更ファイルとviewerの変更ファイルの重なりは0件で、cherry-pickは競合なし。`main.js` と `render-loop.js` は元の検証済みblobと一致し、productionコードの追加修正は不要だった。

## 再利用した検証

統合worktreeで固定lockの依存を既存storeからofflineで用意し、production buildを再作成した。JS bundleは661,246 bytes、SHA-256 `3575dcb988cec4453181997856432ce00d0c4a02a163a7c96f49f62f9c418e9f`、offline shellは `6d7bb416c073e5a3144b43c7143a2d0831abc6af92051d9108900057fe72d8ee` で元のbuildと一致した。

公開fixtureの3,036 bytes、144 triangles、SHA-256 `0bd314b3dc7e691f843293c490f4e27c6be3bc61bba28aad31dd12ed776d5f08` も一致。既存33ユニットテスト、5ビューの画像比較、WebGL context復旧、オフライン保存・撮影・ZIP・retryの既存ブラウザ回帰は、入力・source・依存・buildが同一なので成功結果を再利用した。元の [計測証跡](evidence/idle-rendering-20261002/provenance.json) は変更していない。

## 描画要求の追加検証

[tests/render-transitions-browser.cjs](tests/render-transitions-browser.cjs) を専用headless Edgeで実行した。23ケース成功、pageerror 0件。idle判定はケースごとにprobeを初期化し、新しい描画要求を前ケースの計数で見落とさないようにした。

| 確認対象 | 結果 |
| --- | --- |
| GLB取得を保留し、ロード待ちで静止する | 不要な描画を継続しない |
| ロード完了前にサイズ・濃さを変更する | 読込後のmodelを最新設定で表示する |
| 初期からhiddenの間にmodelを読み込み、表示設定を変更する | hidden中は描画0、復帰時にmodelを描画する |
| controls dampingの途中でhidden/visibleにする | 休止中は描画0、復帰後に減衰を完了する |
| ブラウザの実際のCDP freeze/resume | 静止後の表示変更と、継続中のカメラ描画が再開する |
| カメラ許可拒否、許可待ち取消、track終了 | viewerへ戻り静止する。遅れて届くstreamは終了し、勝手にカメラを再開しない |
| カメラ中のvisibility・pagehide/pageshow | 停止したstreamからviewerへ戻って再描画する |
| 撮影、保存済み下書き、Escape取消、視点リセット | カメラの継続描画、viewerの再描画とその後の静止を保持する |
| 送信失敗、同一内容の再試行、次の写真、カメラ再開 | 画面状態を保持し、必要時に再描画する |

fixtureが実際に可視であることをcanvas画像の色と三角形数で確認した。復帰後・最終viewerの不透明画像は、元の [after/opaque.png](evidence/idle-rendering-20261002/after/opaque.png) とPNGのSHA-256まで一致した。送信APIはローカル応答へ差し替え、実送信していない。

実行は既存CIと同じ `VITE_OBSERVATION_API_URL` を指定したproduction buildを専用preview URLで配信する。PowerShellでは以下を使用できる。

```powershell
$env:VITE_OBSERVATION_API_URL='https://otw-observation-api.open-tokyo-world-observation-api.workers.dev'
pnpm build
# 専用previewを起動した後
$env:BROWSER_CHANNEL='msedge'
$env:TEST_URL='http://127.0.0.1:<専用port>/'
node tests/render-transitions-browser.cjs
```

`BROWSER_CHANNEL` を省略するとPlaywright Chromiumを使う。`PERF_OUTPUT` は追加検証の記録先を変更する。結果・source blob・再利用根拠は [integration-pr47.json](evidence/idle-rendering-20261002/integration-pr47.json) にある。全ログ、build、追加画像は検証worktreeのignored `data/local/viewer-integration/` に保存した。

統合mainのportable checksは `python -m unittest discover -s tests` で232件、225成功・7skip。skipは任意のproduction Shapelyがない2件と、OpenCVがない5件。viewer外の依存は追加していない。

## 性能値のレビューと限界

Before/Afterは同じブラウザ版、960×900 viewport、device scale factor 1、model、カメラ初期値、照明、濃さ、アンチエイリアスを使用した。アセット表示後の静止状態を約2.5秒×3回測定し、以後に操作を試している。モデルが非表示になったための0描画ではないことは、元の画像一致と今回の復帰・遅延ロード時の可視確認で裏付けた。

361→0描画、4,693→0 draw call、ページTaskDuration中央値151.047→0.555msは静止アイドルの不要処理の削減を示す。CPU時間は計測用ラッパーを含む当該ページのCDP差分で、端末全体の使用率ではない。カメラの継続描画カウンターからFPS改善率を算出しない。電池、発熱、GPU消費電力は未測定。

headless Edgeではタブ切替だけでは`document.hidden`が変わらなかった。visibilityイベントを制御した状態遷移と、実際のブラウザfreeze/resumeを別に検証した。実機Safariの背景タブ・BFCache動作を確認したとは扱わない。次は親側の統合確認後、iPhone Safariで実カメラ、背景復帰、回転、濃さ変更を確認する。

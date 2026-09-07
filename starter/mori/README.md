# 森JPタワーの独立生成・置換試験

固定した公式PLATEAUの2ファイルから、森JPタワーの断面と低層部を取得し、詳細外装・入口・テラス・床と屋根を生成する。旧都市blend、source_mori.npz、profiles.json、旧制作ディレクトリは不要。

**技術的な独立再生成試験。詳細モデル全体の自由な再配布許諾が完了したスターターではない。** [出典と現在の許諾範囲](NOTICE.md)を確認する。既存の広場6部品・指定MITコードの許諾は保持する。

## 実行

Python 3.12とBlender **4.5.1 LTS**。CLIは標準ライブラリ、workerはBlender同梱NumPyとDracoを使用する。Blenderのパスを自分の環境に置き換える。

```sh
python starter/mori/run.py --blender BLENDER --output runs/mori-first
```

公式2ファイルを新規取得しhash確認、生成、別processでBefore/Afterを再open、4視点×2枚をrenderする。出力先は毎回新しいディレクトリを指定する。既存結果は上書きしない。CPUを明示し、各processは20分でタイムアウトする。ネットワーク取得失敗時の旧cacheへの暗黙fallbackはない。

明示的に取得済みの同一ファイルを使う場合のみ `--inputs PATH` を追加する。そのディレクトリには `tileset.json` と `data221.b3dm` が必要で、同じhash検査を行う。

`review.html`を画像と同じ場所で開く。`before.blend`は公式基盤＋広場、`after.blend`は詳細置換後。`scene.blend`は基盤構築中の中間ファイルで、採用候補ではない。大きいblend・公式Texture・入力データはGitへ追加しない。

## 部位と出典

- 100m断面160方向の半径を公式地物から取得。3回平滑化・256分割から外装生成。
- 四隅の頂部と暗いガラス、胴体から頂部に連続する縦線は既存レビュー済みadapterを適用。
- 低層部1,070三角形を公式地物から取得。50m閾値をまたぐ隣接面欠落を検査。
- 入口3部品とテラス4部品は既存の独立生成関数を再利用。
- 旧モデルにある推定床・天井・屋根の形状を最小限で再生成し、空洞の見え方を防ぐ。家具・ブラインド・屋上設備は含めない。
- 地物ID `bldg_433bc5b3-db73-4644-ac24-a28d51b7ecd5` を一度だけ置換。batch 5を恒久IDとして使用しない。周囲23地物と広場6部品の形状・UV・材質・transformを維持する。

角度18.28125/109.6875/198.28125/286.875度、頂部331.1m、屋根318.6–318.95mは旧表示座標上の推定値。実測標高ではない。地物ごとのENU原座標と表示高さ移動は`georeference.json`、部品一覧・指紋・断面は`replacement.json`、使用コードhashと取得元は`run.json`に記録する。

## 検証

```sh
python -m unittest discover -s tests
python tests/mori_standalone_blender.py --blender BLENDER --run runs/mori-first --output runs/mori-negative
```

後者は正常runのコピーを意図的に壊し、屋根欠落・周囲建物の変更・材質リンク切断・対象建物の重複が、別processで拒否されることを確認する。正常runは変更しない。

通常検証は保存後再open、入力画像pack/hash、部品集合、メッシュ・UV・主要材質node/links・transformの指紋、有限座標、ゼロ面積三角形、四隅の頂部、非発光ガラス、屋根面、対象の二重配置、周囲の不変性、全景カメラ枠、PNGを検査する。試験上限は200万三角形・100MB/scene。全node group・全modifier・実物の精度を保証するvalidatorではない。

比較は「公式PLATEAUから詳細モデルへの置換」。旧承認済みシーンと完全に同じ画像になることを証明するものではない。昼光rigは今回の共通比較用。地形・道路の接続、屋上設備、推定内装の省略による見え方、別PC・別OS、人間の新画像レビューは残る。[実行記録](verification.json)

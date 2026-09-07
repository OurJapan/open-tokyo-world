# 森JPタワー入口前：歩行空間の小範囲修正

Issue #7。PR #6を取り込んだmain `a7ae648`を起点とする候補。承認済み建物・入口・屋上テラスを保持し、入口前の20m×14.5mに限定して舗装と植栽を追加します。

## 原因の調査

旧ローカルOSM snapshotのway `1443867470`は `area=yes`, `highway=pedestrian`, `name=中央広場`, `surface=paving_stones`。旧 `work/tokyo60/build_city.py` はareaタグを分岐せず、この閉じた輪郭の各辺を幅9mの道路として生成していました。路面統合を経て、現在のasphalt・gutter・pavementメッシュに残っています。地下道は旧処理で除外しており、今回の現象は地下道を地表へ表示したものではありません。

25地点の地面検査のうち9地点が道路層に当たり、9地点ともこの歩行者領域の輪郭から5.55m以内でした。[出典タグと距離検証](mori-plaza-source-audit.json)。これは保存済みsourceの確認であり、現在のOSM API取得結果ではありません。

[森ビルの施設概要](https://www.mori.co.jp/projects/azabudaihills/facilities/)と[公式1Fマップ](https://www.azabudai-hills.com/floor_map/mori-jp_tower-plaza_1f.html)、[PCPA入口写真](https://pcparch.com/media/pages/work/azabudai-hills/a7d08d332d-1737998439/azabudai-hills-main-entrance-crop-960x-q80.jpg)を照合。確認日2026-09-07。The Cloud（アリーナ大屋根）は入口庇とは別です。参考写真の撮影日・個別の再配布許諾は不明です。写真をTextureとして使用していません。

## 候補の範囲・推定

既存入口原点 `(-419.80,290.82)`、長手方向 `(2,-1)/sqrt(5)`。local u=-10〜10m、入口から外向きv=7.5〜22mに限定します。これは写真から測量した境界ではなく、既存入口と検出された歩行者領域の誤表現をつなぐ作業範囲です。位置登録の確度は中、舗装寸法・植栽帯配置・樹種・樹高は推定です。

入口端の舗装高は約0.383m（既存apron 0.38mと差3mm）、外側へ約0.303mまで緩やかに下げます。中央約14mは植栽を置かず、両端に低木と計4本の樹木を配置します。これは現実の樹木本数の断定ではありません。隣接範囲の道路誤表現と段差は今後の課題として残ります。

## 変更契約

旧道路4objectは名前と変更前mesh hashを固定。高さ1m以下・指定矩形内だけを切り取ります。交差する面は矩形境界で分割し、矩形外の面を残します。旧頂点は全数保持し、対象外面のindex列を保存します。道路全体の削除は行いません。

新規objectは `OTW Mori entry plaza / paving`, `/ planters`, `/ planting` の3つだけ。屋上用のslotを転用せず、地上部品名で既存Mori collectionへ追加し、地物IDを設定します。既存object名が存在すると停止。review契約は宣言した新規objectが正確に存在することを要求し、未宣言の追加・削除・建物変更を拒否します。

## 再実行

ローカル入力は、PR #6で承認されたcandidate.blend（556267519 bytes、SHA-256 `a5ec1c138fda66cc30f0dbfbe3ef8945f4c62baa80b3c4e7184ed1248c722885`）。配布対象ではありません。旧入力lockは保持し、今回専用のlockと空mesh例外の入力hashを固定しました。

```sh
python -m unittest discover -s tests
python scripts/review.py --blender BLENDER --input ACCEPTED_TERRACE_BLEND --lock manifests/mori-terrace-accepted.json --features areas/tokyo-tower/mori-plaza-features.json --cameras areas/tokyo-tower/mori-plaza-cameras.json --patch patches/mori-plaza-v1.json --output NEW_RUN --device OPTIX --width 960 --height 540 --samples 24 --timeout 1200
BLENDER --factory-startup --background --disable-autoexec --python-exit-code 1 --python scripts/validate_mori_plaza.py -- --before NEW_RUN/before.blend --after NEW_RUN/after.blend --output NEW_AUDIT.json
```

保存後の再open・素材不変・許可外変更を検証し、追加部品の閉じた辺・有限座標・非ゼロ三角形、道路の矩形外面積保存と旧頂点一致を別processで確認します。6視点の同条件Before/Afterをローカル比較ページへ保存します。人間の画像レビューは未完了です。

道路meshは切り分けた薄い面であり、全都市のwatertightnessを保証しません。新規部品の閉じた辺検査も、重なりの全検出・測量精度・バリアフリー法規適合を保証するものではありません。固定領域外の同種誤表現、元航空写真の古い地表、独立した第三者環境での再構築、データ配布権は継続課題です。

公開対象は独自コード・数値検証・出典参照のみ。実都市blend・Texture・比較画像・元OSM geometryはローカルに保持します。OSM由来のモデルについてはOpenStreetMap contributorsとODbLの出典・条件を継承する必要がありますが、今回のPRで既存資産全体の配布権を確定したとは扱いません。

## 検証結果

28契約テスト・Blender統合2ケース・6視点12画像が成功。既存変更は路面3objectのみ（paintは一致）、地上3部品を追加し、他の既存objectと画像素材は不変。総polygon増分95,248（約0.24%）。別process検査で道路の範囲外面積誤差は各0.00012m²未満、新規形状の閉じた辺・非ゼロ面を確認しました。

初回描画の最終視点に別のBlender検査が重なり、Before46.625秒／After83.344秒となりました。検査を同時実行せず両方を再描画すると、Before53.297秒／After38.250秒で遅延は再現しませんでした。これは少数回の測定であり、一般的な性能改善の証明ではありません。[数値結果](mori-plaza-v1-validation.json)。

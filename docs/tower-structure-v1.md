# 東京タワーの足元・階段・昇降設備の外観修正

塔脚下で欠けていたフットタウンの外観を補い、屋上からメインデッキへ続く階段と下部昇降路、メインデッキとトップデッキの間の屋外昇降路を制作する候補です。公式写真と施工・メーカー資料で存在や見え方を確認し、既存cityに合わせた寸法で静的な外観を表します。実測モデル、構造設計、エレベーターの稼働機構やアニメーションではありません。

## 固定入力と変更範囲

[構造修正専用の入力lock](../manifests/tower-structure-input.json)で、PR #56の統合候補を固定します。630,656,265 bytes、SHA-256は `aa80b552f267d935d3c5d943ac95d0d410d6ec7abb170346bef707eee6cae2e2` です。[統合記録](tokyo-tower-city-repairs-v1.md)と[検証記録](tokyo-tower-city-repairs-v1-verification.json)に対応し、構成は **PR #47・#49・#51・#52・#56** です。PR #54・#55などの別候補は含みません。今回の修正は、この塗装帯・トップデッキ窓下端を含む入力に対する構造の増分としてレビューします。

通常のcity登録は[採用済みcityのlock](../manifests/mori-plaza-connection-accepted.json)、SHA-256 `9c142f54cc85689cb8a8bc00794dfe8e9b6bc9098f121c9fb02cdbc1aa3dbbc4` のままです。構造修正専用の入力固定は、通常のcity登録の変更や別候補の採用を意味しません。

[実装](../scripts/tower_structure_v1.py)は対象feature `otw:jp:tokyo:minato:tokyo-tower` と変更前メッシュhashを確認し、旧中央コア・階段の限定部分を置き換えます。[フットタウン生成helper](../scripts/tower_foottown_v1.py)は建物外壁・開口・ガラス・屋根・屋上柵を組み立てます。追加部品は専用collection `OTW Tokyo Tower structure v1` にまとめ、二重適用を拒否します。

主な内容は、フットタウンの暗褐色の外壁と屋上、屋上の階段入口、折返し階段と踊り場、細い下部ガラス昇降路、上部の開放型支持フレーム・ガイド部材・小さな救出床2箇所、静止したかごの外形です。塔脚と既存台座の接点には小さなプレート・締結部を加えます。地下基礎は作らず、既存の塔脚・アーチや展望台を資料の不確かな寸法に合わせて移動する変更は含めません。

## 根拠と推定の区別

閲覧日は全て **2026-10-03** です。URL、資料内位置、写真で観察した内容、未確認事項は[出典JSON](../areas/tokyo-tower/tower-structure-sources.json)に記録します。

| 対象 | 資料で確認したこと | この候補での近似 |
|---|---|---|
| フットタウン | [東京タワーの施設案内](https://www.tokyotower.co.jp/foottown/)は塔脚下の建物、1Fの展望台行きエレベーター、屋上の外階段入口を案内。[竹中工務店](https://www.takenaka.co.jp/solution/asset/project/07/)は鉄筋コンクリート造と記載 | 旧モデル由来の73×58m外形、4層の外壁区分、屋上高さ16.2mを使用。窓・入口・屋上設備の位置と寸法は推定。公式案内の1F・2F・3F・5F・RFという表示から、実物がこの4層寸法だとは判断していません |
| 下部中央の見え方 | [公式の階段写真](https://www.tokyotower.co.jp/foottown/20c72pu2d7b.html)と[東京タワー提供の外観写真](https://www.mebs.co.jp/cases/multiple-solutions/interview/1199875_1508.html)で、中央の細い昇降設備・赤い階段、外周トラスとの間の空隙を確認 | 下部昇降路は幅約4.4mのガラスと金属フレーム。正確な断面や内部配置は再現していません |
| 屋上からの階段 | 公式説明はフットタウン屋上からメインデッキまで約600段。写真に折返し、踊り場、赤い手すりが見える | 46折返し区間×13段＝598段。これは約600段の外観を表す制作値であり、実物の正確な段数ではありません。階段幅、蹴上げ、踊り場、手すりの細部は推定です |
| 上部昇降路 | [三菱電機技報2018年9月](https://www.giho.mitsubishielectric.co.jp/giho/pdf/2018/1809.pdf)の冊子22頁は当該エレベーターに昇降路壁がないことを明記。[宮地技報No.28](https://www.miyaji-eng.co.jp/technology/newsletter/media/28/no28-p064-070.pdf)の冊子65頁は両展望台間の中央にシャフト補強を指示 | 外壁を張らず、幅約3.6mの縦フレーム、疎な斜材、ガイド部材、塔体への支持材を追加。断面寸法・支持間隔・中央配置・接続形状は推定です |
| 中間救出床 | [施工当事者の説明](https://www.mebs.co.jp/cases/multiple-solutions/interview/1199875_1508.html)は中間の救出階出入口を2箇所設けたと記載 | Z=184m・217mに小さな床と柵を配置。2箇所という存在は資料に基づき、位置・面積・形状は推定です |
| 塔脚の接点・かご | 公開写真で鉄骨・昇降設備を確認できますが、今回の参照画像から締結部の寸法やかご位置を確定できません | 既存接点へのプレート・締結部、静止かごは外観を補う推定表現です。機構の整合性・可動性を示しません |

数値は `legacy-tokyo-display-v1` のローカル座標で、測量された標高ではありません。フットタウンの屋上柵は1.1m、階段はZ=16.2〜145.1m、下部昇降路はZ=0.45〜145.35m、上部フレームはZ=154.0〜246.1mとして既存形状につなぎます。色・反射・ガラスの設定も写真を参考にした近似であり、測色値ではありません。

屋根には下部昇降路を通すため、中心からX・Y各±2.35mの開口を設けます。屋上の階段入口にはモデル西側に幅1.4m・高さ2.1mの開口を設けます。いずれも既存モデルに合わせた制作寸法で、実物の開口寸法や入口方位は未確認です。上部のロープ状部材は、静止かごを貫通しないよう、かご天井Z=203.94mからZ=246.0mまでに限定します。これは外観上の補足で、ロープ経路全体や昇降機構の再現ではありません。

階段上端Z=145.1mは、入力cityの `Photo based main deck` にある床の高さに合わせています。このcityでは旧タワーのメインデッキ床が削除され、現在の写真ベース内装でも中央約±9mの床面が省略されています。外階段の終端はこの中央設備区画内です。これは既存モデルの状態を述べたもので、実物の床欠落を意味しません。内部ドアや設備区画から客用床までの通行可能経路は今回の制作対象外です。

## 展望台の高さを維持する理由

運営者はメインデッキを150m、トップデッキを250mと案内しています。一方、宮地の全体立面図にはH11の `GL+120.000m`、H23の `GL+223.500m` という表示があります。これらが同じ測定基準・部位を指すことも、差の理由が海抜、敷地基準、床と梁の違いであることも、今回の一次資料では確認できませんでした。

また、三菱電機の公表する約85mはエレベーターの昇降行程であり、両展望台の外形間隔や支持フレームの全長と同一ではありません。**この候補では既存の両展望台の位置・形状を維持します。** 上部部材の高さは既存モデルへの接続値であり、営業上の150m／250mや技報の図面表示を実測寸法に読み替えたものではありません。

宮地の図には工事用ステージなどの仮設物も含まれます。図中の線や床を全て恒久的な外観としてモデル化していません。現在の上部昇降路全体を外側から近接撮影した一次写真は確保できておらず、写真の方位・撮影時点も未確定です。

## 参照素材と配布

参考写真・PDFは閲覧と形状判断に使う資料であり、リポジトリやモデルへ同梱しません。ローカル控えはGit管理外の `data/local/references/tower-structure-research/` に置きます。公開URLで閲覧できることを転載許諾とは扱いません。参照写真を貼り付けたテクスチャも生成しません。

この変更は旧都市全体の配布許諾を与えるものではありません。元city、第三者素材、他のモデル資産の利用条件は既存の許諾記録に従います。比較画像の共有は、その画像の公開条件を確認して別途記録します。

## 検証と採用判断

[9視点のBefore/After画像18枚](../renders/previews/tower-structure-v1/README.md)を公開しています。[検証結果](tower-structure-v1-validation.json)と[画像・実装hash](../renders/previews/tower-structure-v1/evidence.json)で入力、保存結果、比較画像を対応付けています。形状・描画コードは `0254578b2a25cad1a7dac881b2435b5c2da74636` です。

- Blender 4.5.1 LTS、OptiX、1280×848、32 samples、seed 0。各ペアのカメラ・照明・描画条件は一致しています。
- 5フェーズの実city検証が成功。既存3メッシュの限定部分を変更し、17メッシュを追加、その他の既存オブジェクトと依存素材のfingerprintは保持しました。既知の空メッシュ5個とmodifierに関する警告は変更前後で同じです。
- 別Blenderプロセスで保存後のcandidateと固定原本を再読込。追加17メッシュの閉面・有限座標・面の向き、598段と踊り場、屋上開口・入口、ガイド・ロープ終端、脚部プレートと締結部を検査しました。橙色／白色鉄骨の残存頂点・面・材質番号・smooth設定・ベベル設定を原本と完全照合し、原本・candidateとも検査前後でhash不変でした。
- portable checksは358件実行、350件成功、環境依存8件スキップ。構文検査とdiffcheckも成功しています。

画像レビューではフットタウン、階段、昇降路の追加と周辺の保持を確認しました。上部近接では既存主柱やリング梁がかご・ガイドの一部に重なり、救出床の細部も全景だけでは判定できません。保存メッシュ検査と合わせて評価してください。人間による採用判断とマージは未完了です。

再現には登録済み原本とBlender 4.5.1が必要です。出力先は新しいディレクトリを指定してください。

```text
python scripts/review.py --blender <Blender実行ファイル> --input data/local/inputs/tower-structure-pr56/after.blend --lock manifests/tower-structure-input.json --cameras areas/tokyo-tower/tower-structure-cameras.json --features areas/tokyo-tower/tower-structure-features.json --patch areas/tokyo-tower/tower-structure-patch.json --output data/local/reviews/tower-structure-reproduce --device OPTIX --width 1280 --height 848 --samples 32
python scripts/validate_tower_structure.py --blender <Blender実行ファイル> --input data/local/reviews/tower-structure-reproduce/after.blend --original data/local/inputs/tower-structure-pr56/after.blend --output data/local/reviews/tower-structure-reproduce/saved-geometry-validation.json
python -m unittest discover -s tests
```

技術検査の成功は実物精度、歩行可能性、構造安全性、昇降機としての適合性を保証しません。ローカルの完全な実行記録はGit管理外の `data/local/reviews/tower-structure-final-03/` にあります。

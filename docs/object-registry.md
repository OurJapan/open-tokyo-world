# 地物・モデル・配置を共通管理する

建物だけでなく道路、地形、植栽、設備、看板などを扱う。分類名は検索や種類別QAに使い、置換処理を建物名やBlenderのobject名へ固定しない。

## 今回実装した範囲

`scripts/object_registry.py`はJSON台帳と版固定lockから、地物の追加・置換・抑制・材質変更を含む組み立て計画を生成する。Blenderなしで実行でき、既存のcontracts CIで検証する。実メッシュの読込・切断・組立・描画はまだこの共通CLIに接続していない。既存のMori/Tower runnerを置き換えたと表示しない。

```sh
python scripts/object_registry.py --registry registry/example.json --lock registry/example.lock.json --output runs/objects/plan.json
python -m unittest discover -s tests
```

出力は新規ファイルのみ。`registry/example.json`は6分類・7地物・8部位の合成テストデータで実都市ではない。hashはテスト用ラベルを識別するダミー値で、モデルファイルをダウンロードできない。実ファイルの配布・地理整合・render成功を示す例ではない。

## 管理する単位

| 項目 | 内容 |
|---|---|
| feature.id | 現実の対象や配置を追跡する固定ID。データ供給元のIDから独立 |
| kind | building / road / vegetation / street-furniture / terrain / signage等。独自分類も許す |
| owner_area | 地物の管理責任を持つArea。境界上でも正本は一つ |
| parent | 建物と入口、道路と設備群などの包含関係。循環を禁止。自動削除はしない |
| parts | 編集可能な部位ID。道路区間、舗装面、橋脚、樹冠など |
| source_binding | 固定source内のobject_id。取込台帳に存在する対象だけ指定 |
| revisions | 地物の採用版・候補版と操作。lockが一つの版を選ぶ |
| models | モデル版のID・version・hash・所在・format・source・許諾。モデルIDは版ごとに一意にする |
| position_m / yaw_degrees | モデルの局所座標から地物frameへの配置。現段階は平行移動とZ軸回転のみ |
| requires | 必要な別地物とその版。道路に接続する設備など。依存順と循環を検査 |
| review_neighbors | 接続部や視認性の影響を確認すべき地物。自動変更の許可ではない |

一本のベンチのモデルは複数の地物から参照できる。各配置には別IDと位置があり、共通モデルを変えた場合は利用している配置を影響対象へ戻す。一つの複雑な地物が複数メッシュに展開されてもIDは保持する。

モデル版の登録はファイルを配布する許諾の証明ではない。出典・観測時点・権利・承認は従来のprovenance/claims台帳へ残す。本plannerはsource/modelの最低限の許諾欄を必須にするが、法的審査や配布可否の自動認定を行わない。

## 操作

- `replace`：既存の部位を指定モデルに置換する。元sourceを変更せず、その部位の描画を抑制する指示を出す。
- `add`：sourceに存在しない部位や新規地物を追加する。既存geometryにaddすると二重表示として拒否する。
- `suppress`：誤重複・撤去などの対象部位を描画しない。履歴と根拠は保持する。
- `material`：geometryを維持し、明示した材質slotのモデル定義を参照する。実際のslot存在・shader適合は消費側adapterの検証が必要。

道路の「一部を置換」は、importerが地物IDと区間IDを持つ独立したsource部位を作った後で行う。単一meshの任意のメートル範囲を本plannerが切断する機能はない。例のsegment-aを置換してもsegment-bのgeometryは残る。道路の縁石だけを変える場合も、縁石を識別できる部位として先に登録する。未分割の同じsource objectを二つの地物から奪い合う指定は拒否する。

材質操作と形状操作を同じ部位に指定するときは、形状を確定してから材質を指定する。抑制と材質変更の併用は拒否する。候補版の計画は`--review-candidates`を明示したときだけ作成し、出力にreview_onlyを付ける。公開配布側はreview_onlyを拒否する必要がある。

## 座標・LOD・版の固定

frameにはm・east/north/upと座標定義を持たせる。異なる局所原点や標高基準を持つ地物を一つの計画へ混ぜると停止する。変換が必要なら、別工程で変換を検証し、変換後のframeと資産版を登録する。frameの文字列一致だけで測地的な整合が証明されるものではない。

lockのprofileが`review`や`far`など、各操作から使用するモデルを選ぶ。指定profileが欠けた場合は暗黙の軽量化やPLATEAUへのfallbackをしない。距離別LODの自動生成・切替は将来のconsumerの仕事。必要地域の地物だけをlockへ選び、一個の全国blendは作らない。

registry_sha256はJSONをキー順・UTF-8で正規化した内容hash。`object_registry.digest(registry)`で計算する。空白のみの変更で版を変えない。source/modelのsha256は実運用では実入力bytesに対する値であり、取得時にも再照合する。planner自身は通信やファイル取得を行わない。

古いregistryとlockを保持すれば、その計画へ戻せる。同じregistry内の別revisionへ戻す場合はlockの選択版を戻す。旧モデルbytesの保存・取得経路がなければ実都市は再構築できないため、配布資産を別途hashで保存する。

## 検証と変更範囲

二重source占有、重複操作、不明部位、追加先の既存geometry、失われた置換先、依存版違い・循環、座標系の混在、profile欠落を停止する。組み立て順はbuild_orderに記録する。planには使う出典とモデルの表示文を保持する。

`affected_features(old_plan, new_plan)`は変更した地物、共通モデル利用者、逆依存、宣言された周辺確認対象を返す。sourceやframeが変わったら保守的に計画の全レビュー範囲へ広げる。これは再検証対象を求める関数であり、キャッシュ付き増分Blender buildそのものではない。隣接関係の登録漏れを空間検索で発見する仕組みは未実装。

道路には接続点・高さ・幅・交差点整合、地形には境界連続性、設備には接地・干渉・歩行空間、植栽には地表と重複配置の種類別QAを追加する必要がある。共通契約の成功を道路ネットワークの正常性や現実精度の証明にはしない。

## 実都市への接続順

1. 森JPタワーの取込側から固定source地物一覧を出し、既存gml_id置換を共通planのsource_bindingへ結ぶ。詳細13部品を部位IDで登録し、周囲23地物不変の既存試験を維持する。
2. 東京タワーの独立77部品へ安定part_idを付け、資産hashと配布経路を固定する。旧表示座標から共通frameへの整合確認、対応PLATEAU地物の特定を終えるまで同じ都市sceneへ無理に混ぜない。
3. 広場・植栽・設備から道路以外の追加例を一つ接続する。同一modelを別featureとして配置し、共通モデルの更新が全配置のレビューへ反映されることを確認する。
4. 実際の道路sourceを選定し区間分割と出典継承を実装する。区間置換・境界・隣接地物不変を保存後再openとBefore/Afterで確認する。
5. 各consumerでhash検証・許諾同梱・依存データの隔離・保存後再openを実装し、planを差し替えるだけで採用版と旧版を再組立できる状態にする。その後にAreaを拡張する。

本PRはこの順序の前提となる共通契約・planner・テストまで。Mori/Towerの実都市adapter統合、道路の実モデリング、モデル配布サービスは未完了。

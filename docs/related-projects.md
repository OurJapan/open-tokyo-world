# 類似プロジェクト調査

調査日：2026-09-07

## 結論

関連するプロジェクトは既に多数あり、PLATEAUとAIの接続、自然言語によるBlender都市編集、参照画像を使った都市生成、生成結果の自己評価までは先行実装がある。一方、今回調べた公開情報では、実在都市を共同管理し、現実との差分IssueからAIによる修正・同条件のBefore/After・人間のPRレビュー・出典付き履歴までを継続運用している、構想全体に一致するプロジェクトは確認できなかった。

これは不存在や世界初の証明ではない。非公開運用、未公開コード、検索に現れない活動は対象外である。Open Tokyo Worldの差別化は「AIで都市を生成すること」よりも、「誰でも報告でき、別のAIも根拠と変更を引き継げる、実在都市の保守運用」に置くのが適切と考える。

## 調査方法と限界

日本の都市データ／MCP、AI都市生成研究、共同地理・3D制作、Issue／PRによる都市修正の4観点から12回検索した。検索候補は延べ115件で、重複・ミラー・フォークを含む。これは独立した115資料を精読したという意味ではない。公式サイト・論文・上流リポジトリを優先し、主要候補についてREADMEだけでなくソース、CI、公開Issue／PRも確認した。

この調査では各生成システムをインストール・実行していない。したがって再現性、実測性能、出力の実物との一致、既存東京タワーシーンへの接続成功は未検証である。「機能あり」は公開実装または明示された機能を指し、本番品質の保証ではない。

## 特に近い実装

### 1. plateau-creative-mcp：PLATEAUをAIから取得・編集・出力

[上流リポジトリ](https://github.com/pixelx-jp/plateau-creative-mcp)は、範囲を指定した建物取得、building_uidによる選択、削除・高さ変更、GLBと付随metadataの出力を提供する。Blenderへの任意接続もあり、日本の実在都市をAIから扱う入口として非常に近い。コードはMIT表記。

ただし実装上、GLBは主に建物の平面形状を高さ方向に押し出したもので、条件によっては12m四方の箱にフォールバックする。PLATEAUの詳細な外観・テクスチャをそのまま高精細に再現するツールではない。単一GLBには面積1km²以下かつ5,000棟以下の制限があり、大きな範囲はmanifestに切り替わる。全国を一つのBlenderファイルにする方式でもない。[形状生成コード](https://github.com/pixelx-jp/plateau-creative-mcp/blob/main/src/export/ThreeSceneBuilder.ts)

Blender連携は接続先がなければ提案する呼び出しを返し、既定の呼び出しはGLBのインポートである。名前だけから「必ず自動レンダリングまで完了する」とは判断できない。CIはNodeのlint・型検査・テスト・build等であり、現実との差分修正を画像でレビューするCIではない。[Blender連携コード](https://github.com/pixelx-jp/plateau-creative-mcp/blob/main/src/tools/renderViaBlender.ts)、[CI](https://github.com/pixelx-jp/plateau-creative-mcp/blob/main/.github/workflows/ci.yml)

**採り入れる候補：** 地物検索、安定した対象指定、範囲ごとの取得、出典の出力。既存Landmarkの高精細モデルを置き換える用途ではなく、周辺基盤の取得・管理層として評価する。

### 2. UrbanWorld2.0／RAISECity：実在地図・街路画像からAIが都市を生成

[UrbanWorld2.0](https://github.com/tsinghua-fib-lab/UrbanWorld2.0)と対応する[RAISECity論文](https://arxiv.org/abs/2511.18005)は、OSM、街路画像、画像解析、建物画像生成・評価、3D生成、Blenderでの組み立てを組み合わせる。実在都市を起点とするAI生成という技術面では最も近い候補の一つ。

公開コードには、生成画像と参照画像をVLMに渡し、品質・整合性を0〜5で評価し、理由をJSONに保存する処理がある。ただし、これは建物の寸法や見えない面まで現実と一致することの検証ではない。画像生成による補完と事実の再現は区別が必要。[評価コード](https://github.com/tsinghua-fib-lab/UrbanWorld2.0/blob/v0.2/src/urbanworld/stage3_imagination/reflect.py)

コード公開を尋ねる古いIssueは残っているが、現在のv0.2ツリーには実装があるため、「未公開」と判断するのは誤り。pyproject.tomlにはMIT宣言があるものの、モデル重み・街路画像・依存アセットの再配布条件まで同じになるわけではない。[パッケージ定義](https://github.com/tsinghua-fib-lab/UrbanWorld2.0/blob/v0.2/pyproject.toml)

**採り入れる候補：** 調査画像からの建物単位の改善、参照画像との比較、修正理由の構造化。Issueと人間のPR承認を中心にした共同保守は別途設計する。

### 3. Blender-MCP-for-city-generation：AIによる都市編集・検査

[リポジトリ](https://github.com/rrrarrra9/Blender-MCP-for-city-generation)はBlender MCPを都市向けに拡張し、地理原点、OSMタイルの読み込み、シーングラフ取得、形状検査、ファサード・道路・植生、viewportレンダリング、USDタイル出力などのツールを提供する。MIT表記で、都市編集用のAPI設計が参考になる。[ツール実装](https://github.com/rrrarrra9/Blender-MCP-for-city-generation/blob/main/src/blender_mcp/city_tools.py)

snapshot／diffはメモリ上のオブジェクト情報の比較であり、永続的な都市の版管理や完全なメッシュ差分ではない。ファサード生成にも既定のパラメータやヒューリスティックがあり、実物のファサードを根拠資料から忠実に修正する保証はない。公開ツリーにGitHub Actionsのworkflowは確認できず、今回確認した公開Issue・PRも空だった。

**採り入れる候補：** 地物単位の編集操作、シーン検査、レンダリング・書き出しのAPI。導入前に実シーンでの検証が必要。

### 4. 国土交通省 3D-City-Model-Generator：画像・AIを使う公式モデル生成

[公式リポジトリ](https://github.com/Project-PLATEAU/3D-City-Model-Generator)と[公式ドキュメント](https://project-plateau.github.io/3D-City-Model-Generator/)には、建物平面形状や画像等から建築物・道路・植生・都市設備を生成する仕組みがある。READMEはLOD1〜3やCityGML出力を説明し、現実の情報からの生成と仮想建築物の生成の両方を扱う。公開ツリーにはBldgGen2025とBridgeUIが存在する。

「PLATEAUを使ってAIで都市を作る」部分は公式側にも明確な先行例がある。ただし、これ自体が参加者の現実差分Issueを処理するGitHub共同保守システムというわけではない。GPU要件もあり、最初の東京タワーPoCに全機能を組み込む必要はない。ドキュメントの利用条件とソース・モデル・データの条件を分けて確認する必要があり、この調査では一式をMITとは判定していない。

### 5. SCRIPT3D：スクリプトを根拠に編集し、画像で確認

[SCRIPT3D](https://github.com/llada60/SCRIPT3D)は、Blender／Infinigenを使い、生成スクリプト・seed・asset metadataを保持しながら自然言語でシーンを編集する。Planner、構造化コマンド、生成、レンダリング、任意の視覚検証と再修正という構造は、目指すAgentループに近い。Apache-2.0表記。

実装には画像からdone／reason／instructionを返す視覚検証がある。ただし、一般的なシーン編集が対象で、地理的な正確さ、情報の観測日、実在都市の報告受付は対象の中心ではない。[視覚検証コード](https://github.com/llada60/SCRIPT3D/blob/main/src/agent/visual_verifier.py)

**採り入れる候補：** 生成スクリプトと対象IDの対応、再実行可能性、編集結果を画像から見直すループ。

## 研究として近いもの：公開状態の違いに注意

| プロジェクト | 近い点 | 調査時点の公開状態・相違 |
|---|---|---|
| [CityX](https://cityx-lab.github.io/) | 地図などを用いたLLM・手続き生成・視覚フィードバックによる都市制作 | [公式GitHub README](https://github.com/cityx-lab/CityX-Lab)はコード公開予定の表記。直ちに再利用できる実装とは扱わない |
| [CityGenAgent](https://citygenagent.github.io/) | 街区と建物を編集可能なプログラムに分解し、自然言語で操作 | 公式ページはCode Coming Soon。実在の特定都市を継続保守する仕組みとは異なる |
| [MajutsuCity](https://github.com/LongHZ140516/MajutsuCity) | 都市生成とAdd／Delete／Edit／Move／Replaceの操作 | 最新READMEは主要framework公開済み、MajutsuAgentコードは未公開のチェック状態。都市の美術表現・生成が中心 |

MajutsuCityは検索キャッシュと最新READMEの公開状況に差があったため、最新のGitHub取得結果を優先した。論文やデモの能力と、現時点で第三者が使えるコードの範囲を分けて評価する。

## 共同運用と全国規模の設計に参考になるもの

### OpenStreetMap＋OSM2World

[OSM2World](https://osm2world.org/)はOSMの建物・道路等の情報から3Dを生成する。2026年の[Object Viewer](https://osm2world.org/blog/2026/05/31/object-viewer-launch/)では地物単位に新しいOSMデータを読み、タグ変更を3Dで試せる。人間の地理情報更新が3Dへ反映される共同改善の考え方は近い。ただしAIがBlenderの変更PRを作るシステムではない。

参考にするのは、地物単位のID、変更履歴、地理情報と表示の分離、局所的な更新。Blenderファイルを地域参加者全員が直接共同編集する必要はない。

### Build The Earth

[Build The Earth](https://buildtheearth.net/)はMinecraft上で地球を1:1で再現する共同プロジェクト。地域ごとに参加者が実在の街を作るという社会的な構造が近い。制作主体は人間の建築参加者で、AIが都市を修正するOSSのモデルとは異なる。コミュニティが公開されていることから、制作物すべてを自由にBlenderへ移して再配布できるとは推定しない。

### Overture Maps／GERS

[GERS](https://docs.overturemaps.org/gers/)は、現実の地物をデータ更新をまたいで識別し、他データと対応付けるための仕組み。[建物スキーマ](https://docs.overturemaps.org/schema/reference/buildings/building/)は建物の地理情報を扱うが、それ自体が高精細な都市3DやAI編集システムではない。

全国に広げる場合の参考は「県ごとの巨大ファイル」ではなく、「同じ建物を継続して識別できるIDと版の関係」。既存のPLATEAU IDとの対応表を持つ設計が候補となる。

## 接続部品として優先して評価したいもの

- [公式PLATEAU MCP Server](https://docs.plateauview.mlit.go.jp/mcp/overview/)：都市データや仕様へのアクセス、対象範囲や建物情報の検索をAIから扱う入口。都市モデルを直接編集する機能とは区別する。
- [plateau-bridge](https://github.com/pixelx-jp/plateau-bridge)：都市単位の建物データ、manifest、出典・対象範囲・IDなどを扱う。全国規模の取得・キャッシュ・対象検索に関する参考実装。公開者の対応都市数を、そのまま全国の完全なデータ整備と解釈しない。
- [PLATEAU-Builder](https://github.com/Project-PLATEAU/PLATEAU-Builder)：CityGMLの編集、外部形状の取り込み、品質管理の参考。人間向けGUIであり、そのまま無人のAgent CIにはならない。

## その他の確認候補

[Unreal Agent Harness](https://github.com/per-simmons/unreal-agent-harness)は、AIによるUnreal編集、viewport確認、修正を結ぶ実験的な実装。Cesium等を使った都市表現も含むが、外部都市データの表示ができることと、編集・再配布できるオープンな都市資産を共同保守することは別の条件である。

[Silicon Baires](https://github.com/Aerolab/silicon-baires)は、Buenos Airesを題材にコード・Blender・WebGLで街を表現し、Agent向け制作指示と視覚チェックを持つ。実在都市のスタイライズされた作品という点で、既存の東京タワー映像からの出発に近い。現実の細かな変化を地理データとして継続反映する仕組みとは異なる。

## IssueからPRまでの公開運用を確認した結果

最も近い実装のうち、plateau-creative-mcp、UrbanWorld2.0、Blender-MCP-for-city-generationについて、公開GitHub APIのPR一覧をstate=allで取得した。調査時点で3件とも空だった。Issueは前2件にあったが、連携提案やコード公開に関する問い合わせで、現実の建物の差分を修正して比較画像とともにMergeした事例は確認できなかった。3件目のIssue一覧は空だった。

この結果から言えるのは、この3リポジトリでは対象の公開PR事例を確認できないということだけである。個人のローカル運用や他リポジトリでの活動、別の公開プロジェクト全体の不存在を意味しない。

## Open Tokyo Worldへの具体的な反映案

1. **生成エンジンを最初から新規開発しない。** 公式PLATEAU MCPや既存取得ツールを評価し、既存の東京タワー・麻布台ヒルズの詳細モデルを保ったまま接続する。
2. **維持管理の単位を定義する。** 地物ID、地理座標、資料、観測日、推定箇所、モデル版、生成スクリプト、レビュー結果をBlender外に保存する。
3. **比較を再現可能にする。** Before／Afterは同じカメラ、画角、照明、レンダー設定で作る。VLMの自己評価だけで承認せず、人間が根拠と画像を見て判断する。
4. **一件を最後まで通す。** 東京タワー周辺の特定の建物について、第三者にも説明できるIssue、修正、検査結果、画像、PRを残す。
5. **新規参加者と別AIで再現する。** 元作者の会話履歴がなくても、資料と作業指示だけで変更を作成・レビューできるかを試す。これが同品質の参加を支える実証になる。
6. **拡張は取得範囲と変更範囲を分ける。** 全国データを一括で詳細化せず、必要な地域を取得し、変更した地物と周辺だけを再生成・検証する。

この方針なら、既存技術と競合する都市生成器をもう一つ作るのではなく、既存技術を使って「AIと人間が現実の都市を更新し続ける」運用を具体化できる。ただし、異なるAIが同じ品質を出すことは自動的には保証されず、共通の受入条件とレビューの実証が必要となる。

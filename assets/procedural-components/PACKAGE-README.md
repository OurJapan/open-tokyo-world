# Open Tokyo World — 樹木・低木と数式材質 v0.1.0

イチョウ3種類・ケヤキ3種類（それぞれ幹と葉の2部品）、低木4種類、材質31種を収録しています。形状は計16メッシュです。旧都市モデルや制作元のフォルダーは不要です。

## 開く

1. ZIPを新しいフォルダーへ展開します。
2. Blender 4.5.1 LTSで `kit.blend` を開きます。追加アドオンやスクリプトの自動実行は不要です。
3. 編集するときは「名前を付けて保存」で作業用コピーを作成します。

`preview.png` で6種類の木と4種類の低木を確認できます。Blenderの「ファイル → アペンド」で `kit.blend` のObjectまたはMaterialから必要なものを別シーンへ取り込めます。幹と葉は同じ種類・番号の組を選んでください。樹木に使われていない塗装・灯具等の材質もMaterial一覧に保存されています。

参照環境はBlender 4.5.1 LTS、Windowsです。同じPCで、ZIP展開後の再読み込み・形状と材質の照合・描画を確認しました。別PC・他OSの実機確認は未実施です。元の街の再現や全都市データの配布ではありません。

## 利用条件と内容確認

指定された独自部分は **CC BY 4.0** です。作者表示、ライセンスへのリンク、変更内容の表示をお願いします。詳しくは同梱の `ASSET-LICENSE.md` と `NOTICE.md` を参照してください。

`provenance.json` は対象部品・材質と許諾の記録、`verification.json` は保存後の検査結果、`inventory.json` はファイルごとのサイズ・SHA-256です。ZIPの外側にある `SHA256SUMS.txt` と照合する場合、Windowsでは次を使えます。

```powershell
Get-FileHash -Algorithm SHA256 .\procedural-components-v0.1.0.zip
```

プロジェクト：[Open Tokyo World](https://github.com/OurJapan/open-tokyo-world)

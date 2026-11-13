# 高速道路マップ(Web版・試作)

## 動かす
    cd highway-map && python3 -m http.server 8000   # → http://localhost:8000
背景地図なしで路線網が表示されます。背景を付けるには `config.js` の `styleUrl` に OSM系スタイルの URL(MapTiler など)を入れます。
キーはブラウザに露出するので、発行元で「許可ドメイン」を制限してください。

## データ(data/)
- `roads.geojson` 路線の線形(色=仮分類 `k`、元の線幅 `w`)
- `facilities.geojson` IC/JCT/SA/PA/スマートIC/料金所/路線番号(`z`=表示開始ズーム、`exact`=実位置が取れたか)
- `roadnames.geojson` 道路名ラベル(点+回転角)
- `tools/transform.json` Scratch座標→緯度経度の暫定係数

## 再生成
    sh tools/build.sh path/to/マップ2026-15.html.sb3

## 既知の限界
- 座標変換は JCT 6か所による暫定フィット(約±0.01°=約1km)。OSM の高速道路データと重ねて精密化する前提です。
- 元データは 1ユニット≒270m の手描きなので、z12 以上では形状が粗いです。
- 路線の色の意味(`k`)は仮の名前です。凡例を確認して `build_geojson.py` の KIND を直してください。
- 路線ID・上下線・接続関係は持っていません(経路検索はOSMデータ側で作る方針)。

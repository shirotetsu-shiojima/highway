// 背景地図と初期表示の設定。ここだけ編集すれば背景地図を差し替えられます。
window.APP_CONFIG = {
  // OSM系ベクタ/ラスタースタイルの URL(例: MapTiler)。空なら無地背景で路線網だけ表示します。
  //   'https://api.maptiler.com/maps/streets-v2/style.json?key=YOUR_KEY'
  // キーはブラウザに露出するため、発行元の管理画面で「許可するドメイン(Referer)」を必ず制限してください。
  styleUrl: '',

  // styleUrl を使うとき、そのスタイルが日本語ラベルを持つ glyphs を提供します。
  // 無地背景のときだけ、同梱の fonts/ を使います。
  fallbackGlyphs: './fonts/{fontstack}/{range}.pbf',
  fontStack: ['Noto Sans Regular'],

  center: [139.75, 35.6],
  zoom: 8.6,
  minZoom: 4.5,
  maxZoom: 15,
  bounds: [[127.0, 30.0], [146.5, 42.5]],  // 北海道・沖縄は対象外
};

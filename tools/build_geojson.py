"""network_raw.json + fac.json → Web 用 GeoJSON(roads / facilities / roadnames) と transform.json。
  python3 build_geojson.py <raw.json> <fac.json> <outdir>
座標変換: Scratch(Gx,Gz) → Web メルカトル。係数は geo.py の最小二乗結果(暫定)。
"""
import json, math, sys, os, re

raw = json.load(open(sys.argv[1])); fac = json.load(open(sys.argv[2])); OUT = sys.argv[3]
os.makedirs(OUT, exist_ok=True)

# ---- 変換係数(geo.py の fit() 結果)。精密化したらここだけ差し替える ----
S, A, B = 418.38, None, None
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geo
anch = [a for a in geo.ANCH if a[0] != 'セントレア'] + [('鳥栖JCT', 6912.21, 4337.85, 130.5231, 33.3786)]
S, A, B = geo.fit(anch)
to_ll = geo.make((S, A, B))
json.dump({'units_per_deg': S, 'a': A, 'b': B, 'note': 'lon=(Gx-a)/s ; mercatorY=(Gz-b)/(s*180/pi)',
           'status': 'provisional: fitted on 6 landmarks, ~±0.01deg'}, open(f'{OUT}/transform.json', 'w'))


def ll(p):
    lon, lat = to_ll(p[0], p[1]); return [round(lon, 5), round(lat, 5)]


# ---- 路線の色 → 仮分類(意味は後で確定) ----
KIND = {'#00c1ff': 'blue', '#1599ff': 'blue2', '#80dfff': 'blue_light', '#8200ff': 'purple', '#c180ff': 'purple_light',
        '#ff7675': 'red', '#ff9797': 'red_light', '#ff9400': 'orange', '#ff8600': 'orange', '#ffa952': 'orange_light',
        '#00ff16': 'urban', '#bababa': 'grey', '#005fff': 'deepblue'}
seen, feats = set(), []
for r in raw['roads']:
    key = (r['c'], tuple((round(x/1.5), round(z/1.5)) for x, z in r['p'][::max(1, len(r['p'])//4)]))
    if key in seen: continue
    seen.add(key)
    feats.append({'type': 'Feature', 'properties': {'c': r['c'], 'k': KIND.get(r['c'], 'other'), 'w': r['w']},
                  'geometry': {'type': 'LineString', 'coordinates': [ll(p) for p in r['p']]}})
json.dump({'type': 'FeatureCollection', 'features': feats}, open(f'{OUT}/roads.geojson', 'w'), separators=(',', ':'))

# ---- 施設 ----
def minzoom(f):
    n, k = f['name'], f['kind']
    if k == '路線番号': return 7.5
    if 'JCT' in n or 'ＪＣＴ' in n: return 8.2
    if k == 'SA/PA' or n.endswith(('SA', 'PA')): return 9.4
    if k == 'スマートIC' or 'スマート' in n: return 10.6
    if k == '料金所': return 10.8
    if k == '一般道直結': return 10.2
    return 9.0 if k == 'IC/JCT' else 9.8


ff = []
for f in fac:
    p = f['pos'] or f['label']
    ff.append({'type': 'Feature', 'properties': {
        'name': f['name'], 'kind': f['kind'], 'fill': f['fill'], 'z': minzoom(f), 'exact': bool(f['pos']),
        'jct': 'JCT' in f['name']}, 'geometry': {'type': 'Point', 'coordinates': ll(p)}})
json.dump({'type': 'FeatureCollection', 'features': ff}, open(f'{OUT}/facilities.geojson', 'w'), ensure_ascii=False, separators=(',', ':'))

# ---- 道路名: 1文字ずつ置かれたテキストを、並び順+距離で連結 ----
names, cur, last = [], [], None
chars = [t for t in raw['texts'] if t['fill'] in ('#00c1ff', '#8200ff', '#ff7675', '#005fff') and len(t['s']) == 1]
for t in chars:
    if last and (t['t'] != last['t'] or math.dist(t['p'], last['p']) > 9):
        names.append(cur); cur = []
    cur.append(t); last = t
if cur: names.append(cur)
rn = []
from collections import Counter
proj = json.load(open(os.path.join(sys.argv[4], 'project.json'))) if len(sys.argv) > 4 else None
ROUTES = sorted({x for t in proj['targets'] if t['isStage'] for v in t['lists'].values() if v[0] == '路線' for x in v[1]}) if proj else []
ROUTES += ['首都高速道路', '東京外環自動車道', '第二東海自動車道']
for ch in names:
    if len(ch) < 3: continue
    cnt = Counter(c['s'] for c in ch)
    cands = [r for r in ROUTES if not (cnt - Counter(r))]
    if not cands: continue
    name = min(cands, key=lambda r: len(r) - len(ch))
    pts = [c['p'] for c in ch]
    dx, dz = pts[-1][0]-pts[0][0], pts[-1][1]-pts[0][1]
    if abs(dx) + abs(dz) < 1:
        rot = 0
    else:
        rot = -math.degrees(math.atan2(dz, dx))
        if rot > 90: rot -= 180
        if rot <= -90: rot += 180
    cx = sum(p[0] for p in pts)/len(pts); cz = sum(p[1] for p in pts)/len(pts)
    rn.append({'type': 'Feature', 'properties': {'name': name, 'rot': round(rot, 1), 'fill': ch[0]['fill'], 'n': len(ch)},
               'geometry': {'type': 'Point', 'coordinates': ll((cx, cz))}})
json.dump({'type': 'FeatureCollection', 'features': rn}, open(f'{OUT}/roadnames.geojson', 'w'), ensure_ascii=False, separators=(',', ':'))
print('roads', len(feats), 'facilities', len(ff), 'roadnames', len(rn))
print([f['properties']['name'] for f in rn][:25])

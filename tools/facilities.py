"""network_raw.json の boxes/texts/leaders/dots から施設(IC/JCT/SA/PA 等)を組み立てる。
  python3 -I facilities.py in.json out.json
箱(塗り+黒枠) に含まれる文字を名称とし、箱の縁に接する引き出し線の反対端 → 最寄りの点(dot)を実位置とする。
"""
import json, sys, math

d = json.load(open(sys.argv[1]))
KIND = {'#00c1ff': 'IC/JCT', '#8200ff': '有料IC', '#d500ff': 'スマートIC', '#ff7675': '一般道直結',
        '#ff9400': '料金所', '#1599ff': 'IC/JCT', '#ffa952': '料金所', '#51d440': '路線番号',
        '#ffffff': 'SA/PA', '#c180ff': '有料IC(未開通)', '#ffc900': '料金所'}


def inside(p, bb, m=0.6):
    return bb[0]-m <= p[0] <= bb[2]+m and bb[1]-m <= p[1] <= bb[3]+m


def dist_to_bb(p, bb):
    dx = max(bb[0]-p[0], 0, p[0]-bb[2]); dz = max(bb[1]-p[1], 0, p[1]-bb[3])
    return math.hypot(dx, dz)


by_tile = {}
for k in ('boxes', 'texts', 'leaders', 'dots'):
    for it in d[k]:
        by_tile.setdefault(it['t'], {}).setdefault(k, []).append(it)

fac, seen = [], set()


def area(bb): return (bb[2]-bb[0]) * (bb[3]-bb[1])


for tile, g in by_tile.items():
    boxes, texts = g.get('boxes', []), g.get('texts', [])
    # 文字 → それを含む「最小の箱」に1対1で割り当てる(隣接する箱の名称が混ざらないように)
    owner = {}
    for ti, t in enumerate(texts):
        c = [(area(b['bb']), bi) for bi, b in enumerate(boxes)
             if b['bb'][0]-0.8 <= t['p'][0] <= b['bb'][2]+0.8 and b['bb'][1]-0.8 <= t['p'][1] <= b['bb'][3]+1.8]
        if c: owner.setdefault(min(c)[1], []).append(t)
    for bi, ts in owner.items():
        b = boxes[bi]; bb = b['bb']
        rows = {}
        for t in sorted(ts, key=lambda t: (-t['p'][1], t['p'][0])):
            k_ = next((r for r in rows if abs(r - t['p'][1]) < 3), t['p'][1]); rows.setdefault(k_, []).append(t['s'])
        name = '\n'.join(''.join(v) for v in rows.values())
        best = None
        for l in g.get('leaders', []):
            for a_, z in ((l['p'][0], l['p'][-1]), (l['p'][-1], l['p'][0])):
                da = dist_to_bb(a_, bb)
                if da < 1.2 and (best is None or da < best[0]): best = (da, z)
        pos = best[1] if best else None
        if pos:
            ds = [(math.hypot(o['p'][0]-pos[0], o['p'][1]-pos[1]), o) for o in g.get('dots', [])]
            ds = [x for x in ds if x[0] < 2.5]
            if ds: pos = min(ds, key=lambda x: x[0])[1]['p']
        key = (name, round(bb[0]), round(bb[1]))
        if key in seen: continue
        seen.add(key)
        fac.append({'name': name, 'kind': KIND.get(b['f'], b['f']), 'fill': b['f'], 'tile': tile,
                    'label': [round((bb[0]+bb[2])/2, 2), round((bb[1]+bb[3])/2, 2)],
                    'pos': [round(pos[0], 2), round(pos[1], 2)] if pos else None})
# タイル重なり部での重複除去: 同名で 8 ユニット以内なら 1 件にまとめる(実位置ありを優先)
fac.sort(key=lambda f: (f['pos'] is None))
uniq = []
for f in fac:
    p = f['pos'] or f['label']
    if any(u['name'] == f['name'] and math.hypot((u['pos'] or u['label'])[0]-p[0], (u['pos'] or u['label'])[1]-p[1]) < 8 for u in uniq): continue
    uniq.append(f)
fac = uniq
json.dump(fac, open(sys.argv[2], 'w'), ensure_ascii=False)
n = len(fac); np_ = sum(1 for f in fac if f['pos'])
print('facilities', n, 'with pos', np_)

"""sb3 (展開済みディレクトリ) から路線網・施設ラベルを抽出して out/network.json を作る。
使い方: python3 -I extract.py <展開ディレクトリ> <出力json>
座標は Scratch グローバル座標 (Gx, Gz)。Gx は東向き、Gz は北向き。
  Gx = 列*480 + (svg_x - rotcenter_x)
  Gz = 行*256 - (svg_y - rotcenter_y)
"""
import json, re, sys, math, collections

SRC, DST = sys.argv[1], sys.argv[2]
proj = json.load(open(f'{SRC}/project.json'))
T = {t['name']: t for t in proj['targets']}

NUM = re.compile(r'[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?')
ATTR = re.compile(r'([\w:-]+)="([^"]*)"')


def parse_path(d):
    """M/l/c/h/v/z だけ対応(このプロジェクトの SVG はこれだけ)。サブパスごとの点列を返す。"""
    toks = re.findall(r'[MmLlHhVvCcZz]|' + NUM.pattern, d)
    subs, cur, x, y, i, cmd = [], [], 0.0, 0.0, 0, None
    sx = sy = 0.0
    def num():
        nonlocal i
        v = float(toks[i]); i += 1; return v
    while i < len(toks):
        t = toks[i]
        if re.match(r'[A-Za-z]', t):
            cmd = t; i += 1
            if cmd in 'Zz':
                if cur: cur.append((sx, sy)); subs.append((cur, True)); cur = []
                x, y = sx, sy
                continue
        if cmd == 'M':
            if cur: subs.append((cur, False)); cur = []
            x, y = num(), num(); sx, sy = x, y; cur = [(x, y)]; cmd = 'L'
        elif cmd == 'm':
            if cur: subs.append((cur, False)); cur = []
            x, y = x + num(), y + num(); sx, sy = x, y; cur = [(x, y)]; cmd = 'l'
        elif cmd == 'L': x, y = num(), num(); cur.append((x, y))
        elif cmd == 'l': x, y = x + num(), y + num(); cur.append((x, y))
        elif cmd == 'h': x += num(); cur.append((x, y))
        elif cmd == 'v': y += num(); cur.append((x, y))
        elif cmd == 'c':
            a = [num() for _ in range(6)]
            p0 = (x, y); p1 = (x + a[0], y + a[1]); p2 = (x + a[2], y + a[3]); p3 = (x + a[4], y + a[5])
            for k in range(1, 5):
                u = k / 4; v = 1 - u
                cur.append((v**3*p0[0] + 3*v*v*u*p1[0] + 3*v*u*u*p2[0] + u**3*p3[0],
                            v**3*p0[1] + 3*v*v*u*p1[1] + 3*v*u*u*p2[1] + u**3*p3[1]))
            x, y = p3
        else:
            raise ValueError(cmd)
    if cur: subs.append((cur, False))
    return subs


def tile_rc(name):
    m = re.fullmatch(r'(\d\d)(\d\d)', name)
    return (int(m.group(1)), int(m.group(2))) if m else None


out = {'roads': [], 'boxes': [], 'leaders': [], 'dots': [], 'texts': []}
sprite = T['スプライト1']
tiles = 0
for c in sprite['costumes']:
    rc = tile_rc(c['name'])
    if not rc: continue
    col, row = rc
    svg = open(f"{SRC}/{c['md5ext']}", encoding='utf8').read()
    g = re.search(r'<g transform="translate\(([-\d.]+),([-\d.]+)\)"', svg)
    tx, ty = (float(g.group(1)), float(g.group(2))) if g else (0.0, 0.0)
    rcx, rcy = c['rotationCenterX'], c['rotationCenterY']
    if rcx == 0 and rcy == 0: continue  # 空コスチューム
    tiles += 1
    def G(px, py):
        return (round(col*480 + (px + tx) - rcx, 2), round(row*256 - ((py + ty) - rcy), 2))
    for el in re.findall(r'<path [^>]*/>', svg):
        a = dict(ATTR.findall(el))
        fill, stroke, sw = a.get('fill', 'none'), a.get('stroke', 'none'), float(a.get('stroke-width', '0'))
        subs = parse_path(a['d'])
        if fill == 'none' and stroke not in ('none', '#000000', '#ffffff', '#808080'):
            for pts, closed in subs:
                if len(pts) >= 2:
                    out['roads'].append({'t': c['name'], 'c': stroke, 'w': sw, 'p': [G(*p) for p in pts]})
        elif fill == 'none' and stroke == '#000000':
            for pts, closed in subs:
                if len(pts) >= 2: out['leaders'].append({'t': c['name'], 'p': [G(*p) for p in pts]})
        elif fill not in ('none',) and subs:
            pts = [G(*p) for s_, _ in subs for p in s_]
            xs = [p[0] for p in pts]; zs = [p[1] for p in pts]
            bb = [min(xs), min(zs), max(xs), max(zs)]
            w, h = bb[2]-bb[0], bb[3]-bb[1]
            if stroke == '#000000' and w > 4 and h > 3:
                out['boxes'].append({'t': c['name'], 'f': fill, 'bb': bb})
            elif fill in ('#ffffff', '#3c3c3c') and stroke == 'none' and w < 4 and h < 4:
                out['dots'].append({'t': c['name'], 'f': fill, 'p': [(bb[0]+bb[2])/2, (bb[1]+bb[3])/2], 'r': max(w, h)/2})
    for tm in re.finditer(r'<text transform="([^"]*)"[^>]*fill="([^"]*)"[^>]*>(.*?)</text>', svg, re.S):
        tr, fill, body = tm.groups()
        m = re.match(r'translate\(([-\d.]+),([-\d.]+)\)(?: rotate\(([-\d.]+)\))? scale\(([-\d.]+),', tr)
        a, b, rot, sc = float(m.group(1)), float(m.group(2)), float(m.group(3) or 0), float(m.group(4))
        chars = re.findall(r'<tspan[^>]*>(.*?)</tspan>', body, re.S)
        vertical = len(chars) > 1 and 'dy="48' in body
        text = ''.join(chars)
        out['texts'].append({'t': c['name'], 's': text, 'fill': fill, 'rot': rot, 'sc': sc, 'v': vertical,
                             'p': G(a, b)})
json.dump(out, open(DST, 'w'), ensure_ascii=False)
print('tiles', tiles, {k: len(v) for k, v in out.items()})

"""Redraw Japanese text in HGPT textures with Korean.

spec (translation/images.json): {"<member path>#<block>": [region, ...]}
member path is relative to work/unp (e.g. "game/title.har/menu    .hpt", "im/im003551.zpt.dec").
region: {"box": [x0,y0,x1,y1], "ko": "텍스트(\\n 가능)", "font": "serif|gothic|serifB|gothicH",
         "align": "center|left|right", "bg": "auto|clear|keep", "size": optional px, "sx": optional max h-scale,
         optional: "edge": null (no outline), "glow": false|[r,g,b,a], "bgfill": [r,g,b,a] (solid erase), "bgx": x (erase rows with colours of column x)}
"""
import sys, os, json, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(__file__))
import hgpt, swz
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = {
    'serif': 'SeoulHangangEB.ttf', 'serifB': 'SeoulHangangB.ttf', 'serifM': 'SeoulHangangM.ttf',
    'gothic': 'NanumSquareNeo-dEb.ttf', 'gothicH': 'NanumSquareNeo-eHv.ttf', 'gothicB': 'NanumSquareNeo-cBd.ttf',
    'gothicR': 'NanumSquareNeo-bRg.ttf',
}

def load(member, blk):
    d = open(os.path.join(ROOT, 'work/unp', member), 'rb').read()
    b = hgpt.blocks(d)[blk]
    idx, cols, s = hgpt.indices(d, b)
    W, H = b['bw'], b['bh']
    arr = np.array([cols[i] if i < len(cols) else (0, 0, 0, 0) for i in idx[:W*H]], np.uint8).reshape(H, W, 4)
    return d, b, np.array(idx[:W*H], np.uint8).reshape(H, W), cols, Image.fromarray(arr, 'RGBA')

def dist2(a, b):
    return sum((int(x) - int(y)) ** 2 for x, y in zip(a[:3], b[:3]))

def analyse(im, box):
    """bg colour(s), ink mask, fill rows, edge colour"""
    x0, y0, x1, y1 = box
    A = np.array(im.crop(box)).astype(int)
    h, w = A.shape[:2]
    border = np.concatenate([A[0], A[-1], A[:, 0], A[:, -1]])
    transparent = (border[:, 3] < 40).mean() > 0.5
    if transparent:
        ink = A[:, :, 3] > 60
        bg = None
    else:
        bgc = np.median(border, axis=0)
        d = np.sqrt(((A[:, :, :3] - bgc[:3]) ** 2).sum(2))
        ink = d > 60
        bg = tuple(int(v) for v in bgc)
    # distance-from-edge layers inside ink
    dist = np.zeros(ink.shape, int); cur = ink.copy()
    for k in range(1, 6):
        er = cur.copy()
        er[1:, :] &= cur[:-1, :]; er[:-1, :] &= cur[1:, :]; er[:, 1:] &= cur[:, :-1]; er[:, :-1] &= cur[:, 1:]
        dist[cur & ~er] = k; cur = er
    dist[cur] = 6
    def med(mask):
        px = A[mask]
        return tuple(int(v) for v in np.median(px, axis=0)) if len(px) else None
    edge = med(dist == 1)
    # the brightest-contrast colour class as "fill": pixels at depth >= 2, else all ink
    inner = dist >= 2 if (dist >= 2).sum() > 10 else ink
    rows = []
    for y in range(h):
        sel = inner[y]
        rows.append(tuple(int(v) for v in np.median(A[y][sel], axis=0)) if sel.any() else None)
    last = next((c for c in rows if c), (255, 255, 255, 255))
    for i in range(h):
        if rows[i] is None: rows[i] = last
        else: last = rows[i]
    fillc = med(inner) or (255, 255, 255, 255)
    has_outline = edge is not None and dist2(edge, fillc) > 3000
    # background rows (left/right columns median) for clearing opaque boxes
    bgrows = [tuple(int(v) for v in np.median(np.concatenate([A[y, :2], A[y, -2:]]), axis=0)) for y in range(h)]
    glow = None
    if transparent:
        semi = (A[:, :, 3] > 20) & (A[:, :, 3] < 200)
        core = A[:, :, 3] >= 200
        if semi.sum() > 0.6 * max(1, core.sum()):
            glow = tuple(int(v) for v in np.median(A[semi][:, :3], axis=0)) + (int(np.percentile(A[semi][:, 3], 75)),)
            corepx = A[core]
            if len(corepx):
                # fill = brightest core colours
                lum = corepx[:, :3].sum(1)
                fillc = tuple(int(v) for v in np.median(corepx[lum >= np.percentile(lum, 60)], axis=0))
                rows = [fillc] * h
            has_outline = False
    return dict(transparent=transparent, bg=bg, bgrows=bgrows, rows=rows, edge=edge if has_outline else None,
                fill=fillc, ink=ink, glow=glow)

def render(text, W, H, st, font, align='center', size=None, sx_max=1.0, fit=0.8, bold=0):
    lines = text.split('\n')
    ow = max(1, round(H / (18 * len(lines)))) if st['edge'] else 0
    best = None
    for s in ([size] if size else range(max(6, int(H * 1.25)), 5, -1)):
        f = ImageFont.truetype(os.path.join(ROOT, FONTS[font]), s)
        bbs = [f.getbbox(l) for l in lines]
        lh = max(b[3] - b[1] for b in bbs)
        gap = max(1, s // 6)
        th = lh * len(lines) + (len(lines) - 1) * gap
        cand = (f, bbs, lh, th, s, gap)
        if th + 2 * ow <= H * fit or size: best = cand; break
    f, bbs, lh, th, s, gap = best or cand  # nothing fits: fall back to the smallest size
    tw = max(b[2] - b[0] for b in bbs)
    cw = int(tw) + 4 * ow + 4
    mask = Image.new('L', (cw, H), 0); dr = ImageDraw.Draw(mask)
    y = (H - th) // 2
    for l, b in zip(lines, bbs):
        lw = b[2] - b[0]
        x = {'center': (cw - lw) // 2, 'left': 2 * ow, 'right': cw - lw - 2 * ow}[align] - b[0]
        dr.text((x, y - b[1]), l, font=f, fill=255)
        y += lh + gap
    sx = min(sx_max, (W - 2) / cw)
    nw = max(1, int(cw * sx))
    mask = mask.resize((nw, H), Image.LANCZOS)
    fillm = Image.new('L', (W, H), 0)
    px = {'center': (W - nw) // 2, 'left': 0, 'right': W - nw}[align]
    fillm.paste(mask, (px, 0))
    if bold: fillm = fillm.filter(ImageFilter.MaxFilter(2 * int(bold) + 1))  # optional stroke thickening
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    if st.get('glow'):
        g = st['glow']; r = max(1.5, H / 14)
        gm = fillm.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(r))
        gm = gm.point(lambda v: min(255, int(v * 2.2 * g[3] / 255)))
        out.paste(Image.new('RGBA', (W, H), g[:3] + (255,)), (0, 0), gm)
    if st['edge']:
        edgem = fillm.filter(ImageFilter.MaxFilter(2 * ow + 1))
        out.paste(Image.new('RGBA', (W, H), st['edge']), (0, 0), edgem)
    rows = st['rows']
    grad = Image.new('RGBA', (W, H)); grad.putdata([rows[min(len(rows) - 1, yy * len(rows) // H)] for yy in range(H) for _ in range(W)])
    out.paste(grad, (0, 0), fillm)
    return out

def quantise(img, pal, allowed=None):
    P = np.array(pal, int)
    A = np.array(img).reshape(-1, 4).astype(int)
    idxs = np.arange(len(P)) if allowed is None else np.array(sorted(allowed))
    Q = P[idxs]
    out = np.zeros(len(A), np.uint8)
    for s in range(0, len(A), 4096):
        a = A[s:s+4096]
        dd = ((a[:, None, :3] - Q[None, :, :3]) ** 2).sum(2) * (a[:, None, 3] / 255.0) + ((a[:, None, 3] - Q[None, :, 3]) ** 2) * 2
        out[s:s+4096] = idxs[dd.argmin(1)]
    return out

def apply(member, blk, regions):
    """returns (new member bytes, before RGBA, after RGBA)"""
    d, b, idx, pal, im = load(member, blk)
    new = im.copy()
    touched = np.zeros(idx.shape, bool)
    for r in regions:
        x0, y0, x1, y1 = r['box']
        st = analyse(im, r['box'])
        W, H = x1 - x0, y1 - y0
        bgmode = r.get('bg', 'auto')
        if r.get('bgfill'): st['bgrows'] = [tuple(r['bgfill'])] * H
        elif 'bgx' in r: st['bgrows'] = [tuple(int(v) for v in im.getpixel((r['bgx'], y0 + yy))) for yy in range(H)]
        if bgmode == 'desat':
            # make only grey/black/white (low-saturation, spread < `desat`, default 60) pixels transparent;
            # keeps coloured artwork (e.g. a logo stroke) crossing monochrome text
            A = np.array(new.crop(r['box'])).astype(int)
            m = (A[:, :, :3].max(2) - A[:, :, :3].min(2)) < r.get('desat', 60)
            A[m] = 0
            new.paste(Image.fromarray(A.astype(np.uint8), 'RGBA'), (x0, y0))
        elif bgmode == 'inpaint':
            # erase only thin glyph-like strokes of colour `ink` (+ `grow` px outline) and inpaint them
            # from their surroundings; for text drawn over pictures. opts: ink [r,g,b], tol, maxw, grow
            import cv2
            A = np.ascontiguousarray(np.array(new.crop(r['box'])))
            ink = np.array(r.get('ink', [255, 255, 255]))
            m = ((np.abs(A[:, :, :3].astype(int) - ink).max(2) <= r.get('tol', 40)) & (A[:, :, 3] > 128)).astype(np.uint8)
            n, lab = cv2.connectedComponents(m, connectivity=8)
            dt = cv2.distanceTransform(m, cv2.DIST_L2, 3)
            keep = np.zeros(m.shape, np.uint8)
            for i in range(1, n):
                c = lab == i
                if dt[c].max() > r.get('maxw', 5) or dt[c].max() < r.get('minw', 0): continue
                if r.get('ring'):  # optional: require a dark/transparent outline around the stroke
                    rg = cv2.dilate(c.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~c
                    px = A[rg].astype(int)
                    dark = (px[:, :3].mean(1) < r.get('dark', 90)) | (px[:, 3] < 128)
                    if len(px) and dark.mean() < r['ring']: continue
                keep[c] = 255
            if r.get('hf'):  # optional: also erase fine detail (thin lines) differing from a median-blurred copy by > hf
                mb = cv2.medianBlur(np.ascontiguousarray(A[:, :, :3]), 9)
                keep[np.abs(A[:, :, :3].astype(int) - mb).max(2) > r['hf']] = 255
            g = r.get('grow', 2)
            if g: keep = cv2.dilate(keep, np.ones((2 * g + 1, 2 * g + 1), np.uint8))
            rgb = cv2.inpaint(np.ascontiguousarray(A[:, :, :3]), keep, 4, cv2.INPAINT_TELEA)
            al = cv2.inpaint(np.ascontiguousarray(A[:, :, 3]), keep, 4, cv2.INPAINT_TELEA)
            new.paste(Image.fromarray(np.dstack([rgb, al]), 'RGBA'), (x0, y0))
        elif isinstance(bgmode, list):  # bg: [r,g,b,a] -> solid fill
            new.paste(Image.new('RGBA', (W, H), tuple(bgmode)), (x0, y0))
        elif bgmode != 'keep':
            if st['transparent'] or bgmode == 'clear':
                new.paste(Image.new('RGBA', (W, H), (0, 0, 0, 0)), (x0, y0))
            else:
                if 'bgfill' in r: g = Image.new('RGBA', (W, H), tuple(r['bgfill']))  # optional solid erase colour
                else: g = Image.new('RGBA', (W, H)); g.putdata([st['bgrows'][yy] for yy in range(H) for _ in range(W)])
                new.paste(g, (x0, y0))
        if r.get('ko'):
            for k in ('fill', 'edge'):
                if r.get(k) is not None: st[k if k == 'edge' else 'rows'] = tuple(r[k]) if k == 'edge' else [tuple(r[k])] * H
            if 'edge' in r and r['edge'] is None: st['edge'] = None
            if 'glow' in r: st['glow'] = tuple(r['glow']) if r['glow'] else None
            txt = render(r['ko'], W, H, st, r.get('font', 'gothic'), r.get('align', 'center'), r.get('size'), r.get('sx', 1.0), r.get('fit', 0.8), r.get('bold', 0))
            if r.get('rot'):  # optional: rotate drawn text by `rot` degrees (counter-clockwise) about the box centre
                txt = txt.rotate(r['rot'], resample=Image.BICUBIC, expand=True)
                dx, dy = x0 + (W - txt.width) // 2, y0 + (H - txt.height) // 2
                sx0, sy0 = max(0, -dx), max(0, -dy)
                new.alpha_composite(txt, (max(0, dx), max(0, dy)), (sx0, sy0, min(txt.width, new.width - dx), min(txt.height, new.height - dy)))
                ry0, ry1, rx0, rx1 = max(0, dy), min(new.height, dy + txt.height), max(0, dx), min(new.width, dx + txt.width)
                touched[ry0:ry1, rx0:rx1] = True
            else:
                new.alpha_composite(txt, (x0, y0))
        touched[y0:y1, x0:x1] = True
    q = quantise(new, pal).reshape(idx.shape)
    q = np.where(touched, q, idx)
    bpp = 8 if b['fmt'] == 0x13 else 4
    flat = q.reshape(-1)
    if bpp == 8: raw = flat.tobytes()
    else: raw = bytes(((flat[1::2] & 15) << 4 | (flat[0::2] & 15)).astype(np.uint8))
    stride = b['bw'] * bpp // 8
    if stride % 16 == 0 and b['bh'] % 8 == 0: raw = swz.swizzle(raw, stride, b['bh'])
    d = bytearray(d)
    p = b['off'] + 0x20
    assert len(raw) == stride * b['bh']
    d[p:p + len(raw)] = raw
    after = Image.fromarray(np.array([pal[i] for i in q.reshape(-1)], np.uint8).reshape(idx.shape + (4,)), 'RGBA')
    return bytes(d), im.crop((0, 0, b['w'], b['h'])), after.crop((0, 0, b['w'], b['h']))

def preview(before, after, path, scale=2):
    W, H = before.size
    sh = Image.new('RGBA', (W * 2 + 6, H), (30, 30, 90, 255))
    sh.alpha_composite(before, (0, 0)); sh.alpha_composite(after, (W + 6, 0))
    sh = sh.resize(((W * 2 + 6) * scale, H * scale), Image.NEAREST)
    sh.save(path)

def frames(member):
    """HGPT sprite frames: list of (x, y, w, h) if the header has a frame table."""
    d = open(os.path.join(ROOT, 'work/unp', member), 'rb').read()
    n, fmt = struct.unpack_from('<HH', d, 0x10)
    if fmt not in (0x13, 0x14) or not (0 < n < 200): return []
    out = []
    for i in range(n):
        x, y, w, h = struct.unpack_from('<4H', d, 0x1c + 8 * i)
        out.append((x, y, w, h))
    return out

if __name__ == '__main__':
    import glob
    spec = {}
    files = [a for a in sys.argv[1:] if a.endswith('.json')]
    for f in files or sorted(glob.glob(os.path.join(ROOT, 'translation/images/*.json'))):
        spec.update(json.load(open(f, encoding='utf-8')))
    sys.argv = [a for a in sys.argv if not a.endswith('.json')]
    outdir = os.path.join(ROOT, 'work/imgprev'); os.makedirs(outdir, exist_ok=True)
    for key in (sys.argv[1:] or spec):
        m, blk = key.rsplit('#', 1)
        _, bf, af = apply(m, int(blk), spec[key])
        preview(bf, af, os.path.join(outdir, key.replace('/', '__').replace(' ', '').replace('#', '_') + '.png'))
        print('ok', key)

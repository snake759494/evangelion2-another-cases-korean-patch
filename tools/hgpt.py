"""HGPT image blocks: 'ppd'+fmt(0x13 8bpp / 0x14 4bpp), w,h, ?, bw,bh, datasize; pixels at +0x20; palette RGBA after."""
import struct
from PIL import Image
def blocks(d):
    out = []; i = d.find(b'ppd')
    while i >= 0:
        fmt = d[i+3]
        if fmt in (0x13, 0x14):
            w, h = struct.unpack_from('<HH', d, i+4)
            bw, bh = struct.unpack_from('<HH', d, i+12)
            size = struct.unpack_from('<I', d, i+16)[0]
            bpp = 8 if fmt == 0x13 else 4
            if bh and (size - 0x20) % bh == 0:   # stride padded to 16 bytes while bw is not (e.g. 144px 4bpp)
                st = (size - 0x20) // bh
                if st > bw * bpp // 8 and st % 16 == 0 and st * 8 // bpp >= w: bw = st * 8 // bpp
            out.append(dict(off=i, fmt=fmt, w=w, h=h, bw=bw, bh=bh, size=size))
        i = d.find(b'ppd', i+4)
    return out
def decode(d, b, swz=None):
    bpp = 8 if b['fmt'] == 0x13 else 4
    px0 = b['off'] + 0x20
    bw, bh = b['bw'], b['bh']
    stride = bw * bpp // 8
    npx = stride * bh
    ncol = 256 if bpp == 8 else 16
    pal_off = b['off'] + b['size'] + 0x10   # 'ppc' 16-byte header, then RGBA (alpha 0x80 = opaque)
    raw = d[px0:px0+npx]
    pal = d[pal_off:pal_off+ncol*4]
    return raw, pal, stride
def to_image(d, b):
    raw, pal, stride = decode(d, b)
    bpp = 8 if b['fmt'] == 0x13 else 4
    W, H = b['bw'], b['bh']
    idx = []
    if bpp == 8: idx = raw
    else:
        idx = bytearray()
        for x in raw: idx += bytes([x & 15, x >> 4])
    cols = [tuple(pal[4*i:4*i+4]) for i in range(len(pal)//4)]
    im = Image.new('RGBA', (W, H))
    im.putdata([cols[i] if i < len(cols) else (255,0,255,255) for i in idx[:W*H]])
    return im.crop((0, 0, b['w'], b['h']))

def _score(idx, w, h):
    s = 0
    for y in range(0, h - 1, 2):
        r0 = idx[y*w:(y+1)*w]; r1 = idx[(y+1)*w:(y+2)*w]
        s += sum(1 for a, b in zip(r0, r1) if a != b)
    return s
def indices(d, b, swz=None):
    """returns (index list W*H over bw x bh, palette tuples, swizzled flag)"""
    import swz as S
    raw, pal, stride = decode(d, b)
    bpp = 8 if b['fmt'] == 0x13 else 4
    def expand(r):
        if bpp == 8: return list(r)
        o = []
        for x in r: o += [x & 15, x >> 4]
        return o
    W, H = b['bw'], b['bh']
    lin = expand(raw)
    if swz is None:
        swz = stride % 16 == 0 and H % 8 == 0   # this game swizzles every texture
    if swz: lin = expand(S.unswizzle(raw, stride, H))
    cols = [tuple(pal[4*i:4*i+3]) + (min(255, pal[4*i+3]*2),) for i in range(len(pal)//4)]
    return lin, cols, swz
def image(d, b, swz=None):
    idx, cols, s = indices(d, b, swz)
    im = Image.new('RGBA', (b['bw'], b['bh']))
    im.putdata([cols[i] if i < len(cols) else (255, 0, 255, 255) for i in idx[:b['bw']*b['bh']]])
    return im.crop((0, 0, b['w'], b['h'])), s

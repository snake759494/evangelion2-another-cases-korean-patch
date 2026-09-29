"""PGF (PSP libfont) reader/writer (revision 2, no shadow data)."""
import struct

HDR = 0x188

def bits_get(buf, pos, n):
    v = 0
    for i in range(n):
        b = pos + i
        v |= ((buf[b >> 3] >> (b & 7)) & 1) << i
    return v

class BitReader:
    def __init__(self, buf, pos=0): self.b = buf; self.p = pos
    def get(self, n):
        v = bits_get(self.b, self.p, n); self.p += n; return v

class BitWriter:
    def __init__(self): self.bits = []
    def put(self, v, n):
        for i in range(n): self.bits.append((v >> i) & 1)
    def pad32(self):
        while len(self.bits) % 32: self.bits.append(0)
    def bytes(self):
        out = bytearray((len(self.bits) + 7) // 8)
        for i, b in enumerate(self.bits):
            if b: out[i >> 3] |= 1 << (i & 7)
        return bytes(out)

def read_table(buf, pos, n, bpe):
    r = BitReader(buf, pos * 8)
    return [r.get(bpe) for _ in range(n)], ((n * bpe + 31) & ~31) // 8

class PGF:
    def __init__(self, d):
        self.d = d
        h = self.h = {}
        h['hdrsize'] = struct.unpack_from('<H', d, 2)[0]
        (h['rev'], h['ver'], h['cmlen'], h['cplen'], h['cmbpe'], h['cpbpe']) = struct.unpack_from('<6i', d, 8)
        h['bpp'] = d[0x22]
        h['first'], h['last'] = struct.unpack_from('<HH', d, 0xb6)
        h['dimlen'], h['xadjlen'], h['yadjlen'], h['advlen'] = d[0x102:0x106]
        h['shlen'], h['shbpe'] = struct.unpack_from('<ii', d, 0x16c)
        p = h['hdrsize']
        if h['rev'] == 3: p += 0x1c
        def tab(n):
            nonlocal p
            t = [struct.unpack_from('<ii', d, p + 8*i) for i in range(n)]; p += 8*n; return t
        self.dim = tab(h['dimlen']); self.xadj = tab(h['xadjlen']); self.yadj = tab(h['yadjlen']); self.adv = tab(h['advlen'])
        self.shmap, n = read_table(d, p, h['shlen'], h['shbpe']); p += n
        assert h['rev'] == 2
        self.charmap, n = read_table(d, p, h['cmlen'], h['cmbpe']); p += n
        self.cptr, n = read_table(d, p, h['cplen'], h['cpbpe']); p += n
        self.fd = d[p:]
        self.fdoff = p

    def glyph(self, idx):
        r = BitReader(self.fd, self.cptr[idx] * 32)
        g = {}
        g['shoff'] = r.get(14)
        g['w'] = r.get(7); g['h'] = r.get(7)
        l = r.get(7); g['left'] = l - 128 if l >= 64 else l
        t = r.get(7); g['top'] = t - 128 if t >= 64 else t
        f = g['flags'] = r.get(6)
        g['shflags'] = (r.get(2) << 5) | (r.get(2) << 3) | r.get(3)
        g['shid'] = r.get(9)
        def pair(flag, tab):
            if f & flag: i = r.get(8); return tab[i]
            return (r.get(32), r.get(32))
        g['dim'] = pair(4, self.dim); g['xadj'] = pair(8, self.xadj)
        g['yadj'] = pair(16, self.yadj); g['adv'] = pair(32, self.adv)
        # bitmap
        w, hh = g['w'], g['h']; n = w * hh; px = [0] * n; i = 0
        while i < n:
            nib = r.get(4)
            if nib < 8:
                v = r.get(4)
                for _ in range(nib + 1):
                    if i < n: px[i] = v; i += 1
            else:
                for _ in range(16 - nib):
                    v = r.get(4)
                    if i < n: px[i] = v; i += 1
        if (f & 3) == 1:
            g['bmp'] = [px[y*w:(y+1)*w] for y in range(hh)]
        else:
            g['bmp'] = [[px[x*hh + y] for x in range(w)] for y in range(hh)]
        g['bits_end'] = r.p
        return g

    def index(self, code):
        c = code - self.h['first']
        if 0 <= c < len(self.charmap):
            v = self.charmap[c]
            return v if v < self.h['cplen'] else None

def rle(px):
    out = []  # list of nibbles
    i = 0; n = len(px)
    while i < n:
        j = i
        while j < n and px[j] == px[i] and j - i < 8: j += 1
        if j - i >= 2:
            out += [j - i - 1, px[i]]; i = j
        else:
            # literal run until a repeat of >=2 starts (max 8)
            k = i
            while k < n and k - i < 8:
                if k + 1 < n and px[k + 1] == px[k]: break
                k += 1
            if k == i: k = i + 1
            out += [16 - (k - i)] + px[i:k]; i = k
    return out

def write(glyphs, template):
    """glyphs: {code: dict(bmp=rows(0..15), left, top, adv(26.6 h))}; template: PGF (header source)."""
    codes = sorted(glyphs)
    first, last = codes[0], codes[-1]
    n = len(codes)
    cmbpe = max(1, (n).bit_length())
    missing = (1 << cmbpe) - 1
    idx = {c: i for i, c in enumerate(codes)}
    cm = [idx.get(first + i, missing) for i in range(last - first + 1)]
    data = bytearray(); ptrs = []
    maxw = maxh = 0; maxasc = maxdesc = 0; maxadv = 0
    for c in codes:
        g = glyphs[c]; bmp = g['bmp']; h = len(bmp); w = len(bmp[0]) if h else 0
        maxw = max(maxw, w); maxh = max(maxh, h)
        maxasc = max(maxasc, g['top'] * 64); maxdesc = min(maxdesc, (g['top'] - h) * 64)
        maxadv = max(maxadv, g['adv'])
        bw = BitWriter()
        bw.put(0, 14); bw.put(w, 7); bw.put(h, 7); bw.put(g['left'] & 127, 7); bw.put(g['top'] & 127, 7)
        bw.put(1, 6)            # H_ROWS, explicit metrics
        bw.put(0, 2); bw.put(0, 2); bw.put(0, 3); bw.put(0, 9)
        for v in (w * 64, h * 64, g['left'] * 64, -g['adv'] // 2 & 0xffffffff,
                  g['top'] * 64, 0, g['adv'], 1152):
            bw.put(v & 0xffffffff, 32)
        for nb in rle([v for row in bmp for v in row]): bw.put(nb, 4)
        # first 14 bits = glyph size in bytes (real libfont copies this many bytes into its cache)
        size = (len(bw.bits) + 7) // 8
        assert size < 1 << 14
        for i in range(14): bw.bits[i] = (size >> i) & 1
        bw.pad32()
        ptrs.append(len(data) // 4); data += bw.bytes()
    cpbpe = max(1, (len(data) // 4).bit_length())
    def table(vals, bpe):
        bw = BitWriter()
        for v in vals: bw.put(v, bpe)
        bw.pad32(); return bw.bytes()
    t = template.d
    hdr = bytearray(t[:HDR])
    struct.pack_into('<6i', hdr, 8, 2, 6, len(cm), n, cmbpe, cpbpe)
    struct.pack_into('<HH', hdr, 0xb6, first, last)
    # keep template maxGlyphWidth/Height: the game sizes its glyph cache from them
    assert maxw <= struct.unpack_from('<H', hdr, 0xfc)[0] and maxh <= struct.unpack_from('<H', hdr, 0xfe)[0], (maxw, maxh)
    hdr[0x102:0x106] = bytes(4)
    struct.pack_into('<ii', hdr, 0x16c, 0, template.h['shbpe'])
    return bytes(hdr) + table(cm, cmbpe) + table(ptrs, cpbpe) + bytes(data)

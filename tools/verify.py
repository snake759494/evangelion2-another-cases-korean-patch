"""Structural verification of a built ISO against the original files (catches container/format bugs
that make the game read garbage, e.g. a wrong size table).  usage: python tools/verify.py OUT.iso

Checks every file that differs from the original:
  BIND  : same version/count/align, every block re-parses as TEXT with identical keys and record headers
  TEXT  : identical keys and record headers
  HAR   : same member count/names/flags, every member decompresses; .evs members keep the exact
          command sequence (op, and for op 1 the 12-byte header), label count; HGPT members keep
          their size and block layout (only pixel bytes may change)
  zpt   : decompresses, HGPT layout unchanged
  EBOOT : bytes change only inside known patch ranges (translated strings incl. their alignment
          padding, SJIS->Unicode table, font-open patch, font path buffer, NID, one relocation)
"""
import sys, os, json, glob, struct
sys.path.insert(0, os.path.dirname(__file__))
import isobuild, bind, textfmt, har, evs, hgpt, ebootpatch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Reader(isobuild.Iso):
    def __init__(self, p): self.f = open(p, 'rb')
    def get(self, p):
        _, _, _, lba, size = self.find(p); self.f.seek(lba * 2048); return self.f.read(size)

errors = []
def err(path, msg): errors.append('%s: %s' % (path, msg))

def text_sig(d):
    recs, (n, to, do) = textfmt.parse(d)
    return n, [(k, a, b) for k, a, b, t in recs]

def check_text(path, o, n):
    try:
        so, sn = text_sig(o), text_sig(n)
    except Exception as e:
        return err(path, 'TEXT parse failed: %r' % e)
    if so != sn: err(path, 'TEXT keys/record headers differ')

def check_bind(path, o, n):
    try:
        (mo, bo), (mn, bn) = bind.parse(o), bind.parse(n)
    except Exception as e:
        return err(path, 'BIND parse failed: %r' % e)
    if mo[:3] != mn[:3] or len(bo) != len(bn): return err(path, 'BIND header/count differs')
    for i, (x, y) in enumerate(zip(bo, bn)):
        if x[:4] != y[:4]: err(path, 'block %d magic differs' % i); continue
        if x[:4] == b'TEXT': check_text('%s[%d]' % (path, i), x, y)
        elif x != y: err(path, 'non-TEXT block %d changed' % i)

def hgpt_layout(d):
    return [(b['off'], b['fmt'], b['w'], b['h'], b['bw'], b['bh'], b['size']) for b in hgpt.blocks(d)]

def check_member(path, name, x, y):
    if name.strip().endswith('.evs'):
        try:
            (lo, co), (ln, cn) = evs.parse(x), evs.parse(y)
        except Exception as e:
            return err(path, '%s EVS parse failed: %r' % (name, e))
        if len(lo) != len(ln) or len(co) != len(cn): return err(path, '%s EVS label/command count differs' % name)
        for (p1, op1, b1), (p2, op2, b2) in zip(co, cn):
            if op1 != op2: return err(path, '%s EVS op sequence differs' % name)
            if op1 == 1 and b1[:12] != b2[:12]: return err(path, '%s EVS op1 header differs' % name)
            if op1 not in (1, 149) and b1 != b2: return err(path, '%s EVS non-text command changed' % name)
        for a, b in zip(lo, ln):
            if not (0 <= b < len(y)): return err(path, '%s EVS label out of range' % name)
    elif x[:4] == b'HGPT':
        if len(x) != len(y) or hgpt_layout(x) != hgpt_layout(y): err(path, '%s HGPT layout/size changed' % name)
        elif x[:0x20] != y[:0x20]: err(path, '%s HGPT header changed' % name)
    elif x != y:
        err(path, '%s unexpected member change' % name)

def check_har(path, o, n):
    try:
        (vo, eo), (vn, en) = har.parse(o), har.parse(n)
    except Exception as e:
        return err(path, 'HAR parse failed: %r' % e)
    if vo != vn or len(eo) != len(en): return err(path, 'HAR version/count differs')
    if o[8 + 4 * len(eo):struct.unpack_from('<I', o, 8)[0]] != n[8 + 4 * len(en):struct.unpack_from('<I', n, 8)[0]]:
        err(path, 'HAR extra header table changed')
    for a, b in zip(eo, en):
        if a['name'] != b['name'] or a['flag'] != b['flag']: err(path, 'member name/flag differs'); continue
        try: x, y = har.data(a), har.data(b)
        except Exception as e: err(path, '%s decompress failed: %r' % (b['name'], e)); continue
        if x != y: check_member(path, a['name'], x, y)

def check_zpt(path, o, n):
    try: x, y = har.read_zpt(o), har.read_zpt(n)
    except Exception as e: return err(path, 'zpt decompress failed: %r' % e)
    if len(x) != len(y) or hgpt_layout(x) != hgpt_layout(y): err(path, 'zpt HGPT layout changed')

def check_eboot(path, o, n, allowed):
    o = o; n = n
    if len(o) != len(n): return err(path, 'EBOOT size changed')
    i = 0; L = len(o)
    bad = []
    while i < L:
        if o[i] != n[i] and not allowed(i):
            j = i
            while j < L and o[j] != n[j] and not allowed(j): j += 1
            bad.append((i, j)); i = j
        i += 1
    for a, b in bad[:20]: err(path, 'unexpected change at 0x%x-0x%x' % (a, b))
    if len(bad) > 20: err(path, '... %d more unexpected ranges' % (len(bad) - 20))

def eboot_allowed():
    ranges = []
    for f in glob.glob(os.path.join(ROOT, 'translation/batches/e*.json')):
        for off, ja, room in json.load(open(f, encoding='utf-8')):
            import re
            l = len(re.sub(r'\{16[0-9A-F]{2}\}', 'xx', ja).encode('cp932'))
            ranges.append((off, ((off + l + 1 + 3) & ~3)))
    D = open(os.path.join(ROOT, 'work/eboot_plain.bin'), 'rb').read()
    rng = ebootpatch.ranges(D)
    last = max(b for a, b in rng)
    ranges.append((ebootpatch.UTAB, ebootpatch.UTAB + 2 * 8000))
    ranges.append((ebootpatch.TXT + 0x652c0, ebootpatch.TXT + 0x65300))
    ranges.append((ebootpatch.PATH_OFF, ebootpatch.PATH_OFF + 100))
    ranges.append((0x1af0b0, 0x1af0b0 + 0x294))            # NID table
    import elf
    for eo, v, t, ob, ab in elf.relocs():
        if v == 0x652d8: ranges.append((eo + 4, eo + 5))
    ranges.sort()
    import bisect
    starts = [a for a, b in ranges]
    def ok(i):
        k = bisect.bisect_right(starts, i) - 1
        while k >= 0 and k > bisect.bisect_right(starts, i) - 40:
            a, b = ranges[k]
            if a <= i < b: return True
            k -= 1
        return False
    return ok

def main(iso_path):
    R = Reader(iso_path)
    base = os.path.join(ROOT, 'work/iso')
    allowed = None
    n_checked = 0
    for root, ds, fs in os.walk(base):
        for f in fs:
            full = os.path.join(root, f)
            p = '/' + os.path.relpath(full, base).replace('\\', '/')
            o = open(full, 'rb').read()
            try: nw = R.get(p)
            except Exception as e: err(p, 'missing in ISO: %r' % e); continue
            if o == nw: continue
            n_checked += 1
            if p.endswith('EBOOT.BIN') and 'UPDATE' not in p:
                allowed = allowed or eboot_allowed()
                check_eboot(p, open(os.path.join(ROOT, 'work/eboot_plain.bin'), 'rb').read(), nw, allowed)
            elif o[:4] == b'BIND': check_bind(p, o, nw)
            elif o[:4] == b'TEXT': check_text(p, o, nw)
            elif o[:4] == b'HGAR': check_har(p, o, nw)
            elif p.endswith('.zpt'): check_zpt(p, o, nw)
            else: err(p, 'changed file of unknown type')
    try:
        R.get('/PSP_GAME/USRDIR/kfont.pgf')
    except Exception: err('kfont.pgf', 'font file missing')
    print('verified changed files:', n_checked, 'errors:', len(errors))
    for e in errors[:60]: print('  ' + e)
    return len(errors)

if __name__ == '__main__':
    sys.exit(1 if main(sys.argv[1]) else 0)

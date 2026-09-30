"""Full Korean patch build.  usage: python tools/build.py OUT.iso
needs: original ISO, work/unp (tools/unpack_all.py), work/eboot_plain.bin, translation/out/*.json
"""
import sys, os, json, glob, struct, re
sys.path.insert(0, os.path.dirname(__file__))
import har, evs, textfmt, bind, ebootpatch, isobuild, mkfont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
ISO = 'Shin Seiki Evangelion 2 - Tsukurareshi Sekai - Another Cases (Japan).iso'
USR = 'work/iso/PSP_GAME/USRDIR/'

# ---------------------------------------------------------------- translations
U = json.load(open('translation/unique_ja.json', encoding='utf-8'))
KO = {}
for f in sorted(glob.glob('translation/out/b*.json')):
    for k, v in json.load(open(f, encoding='utf-8')).items(): KO[int(k)] = v
FIX = [('시그마 기관', 'S2 기관'), ('TA전', 'JA전'), ('~', '～'), ('\t', '')]
def fix(s):
    for a, b in FIX: s = s.replace(a, b)
    return s
JA2KO = {}
for i, ja in enumerate(U):
    if i in KO: JA2KO[ja] = fix(KO[i])
EKO = {}
# binary data that merely looks like SJIS text: never touch
NOT_TEXT = {0x237d74, 0x23a4b4, 0x23c4f0, 0x23c550, 0x23cb08, 0x1d7856, 0x1e6bb4, 0x1e6bbc, 0x22a580, 0x23bff8, 0x23c018, 0x23c038, 0x23c058, 0x23c078, 0x23c1f8, 0x23c218, 0x23c238, 0x23e7c0, 0x23ea38, 0x23eb3e, 0x23eb78, 0x250408, 0x250430, 0x250748, 0x250758, 0x250d88, 0x250e58, 0x2515d0}
for f in sorted(glob.glob('translation/out/e*.json')):
    for k, v in json.load(open(f, encoding='utf-8')).items():
        if int(k) not in NOT_TEXT: EKO[int(k)] = fix(v.replace('~', '-'))
EBOOT_SRC = {}
for f in sorted(glob.glob('translation/batches/e*.json')):
    for off, ja, room in json.load(open(f, encoding='utf-8')): EBOOT_SRC[off] = (ja, room)

# ---------------------------------------------------------------- charset / SJIS mapping
D0 = open('work/eboot_plain.bin', 'rb').read()
def leftovers():
    """Japanese text that stays untranslated (its kanji must keep their SJIS codes)."""
    left = [ja for ja in U if ja not in JA2KO]
    left += [ja for off, (ja, room) in EBOOT_SRC.items() if off not in EKO and off not in NOT_TEXT]
    for x in json.load(open('work/eboot_strings.json', encoding='utf-8')):
        if x['ref'] and x['off'] not in EBOOT_SRC: left.append(x['ja'])
    return left
LEFT = leftovers()
keep = set()
for s in LEFT:
    for ch in s:
        try: b = ch.encode('cp932')
        except UnicodeEncodeError: continue
        if len(b) == 2 and b[0] >= 0x88: keep.add(b[0] << 8 | b[1])
texts = list(JA2KO.values()) + list(EKO.values())
hangul = sorted({ch for t in texts for ch in t if 0xac00 <= ord(ch) <= 0xd7a3})
slots = [c for c in ebootpatch.kanji_slots() if c not in keep]
assert len(hangul) <= len(slots), (len(hangul), len(slots))
H2S = {h: slots[i] for i, h in enumerate(hangul)}
S2H = {c: h for h, c in H2S.items()}
print('hangul', len(hangul), 'kept kanji codes', len(keep), 'untranslated strings', len(LEFT))

bad_chars = {}
def enc(s):
    out = bytearray()
    for part in re.split(r'(\{16[0-9A-F]{2}\})', s):
        if part.startswith('{16') and len(part) == 6:
            out += bytes([0x16, int(part[3:5], 16)])
        else:
            out += enc1(part)
    return bytes(out)

def enc1(s):
    out = bytearray()
    for ch in s:
        o = ord(ch)
        if 0xac00 <= o <= 0xd7a3:
            c = H2S[ch]; out += bytes([c >> 8, c & 0xff])
        elif o < 0x80:
            out.append(o)
        else:
            try: out += ch.encode('cp932')
            except UnicodeEncodeError:
                bad_chars[ch] = bad_chars.get(ch, 0) + 1; out += '・'.encode('cp932')
    return bytes(out)

def tr_bytes(b):
    ja = b.decode('cp932')
    ko = JA2KO.get(ja)
    return b if ko is None else enc(ko)

# ---------------------------------------------------------------- build files
changed = {}   # iso path -> bytes

# imtext.bin
d = open(USR + 'game/imtext.bin', 'rb').read()
meta, blocks = bind.parse(d)
nb = [textfmt.build(b, tr_bytes) if b[:4] == b'TEXT' else b for b in blocks]
changed['/PSP_GAME/USRDIR/game/imtext.bin'] = bind.build(meta, nb)

# battle TEXT (BIND)
d = open(USR + 'btl/btimtext.bin', 'rb').read()
meta, blocks = bind.parse(d)
changed['/PSP_GAME/USRDIR/btl/btimtext.bin'] = bind.build(meta, [textfmt.build(x, tr_bytes) if x[:4] == b'TEXT' else x for x in blocks])

# free TEXT files
for n in ('free/f2info.bin', 'free/f2tuto.bin'):
    changed['/PSP_GAME/USRDIR/' + n] = textfmt.build(open(USR + n, 'rb').read(), tr_bytes)

# EVS inside HAR archives
def evs_repl(op, b):
    try: ja = b.decode('cp932')
    except UnicodeDecodeError: return None
    ko = JA2KO.get(ja)
    return None if ko is None else enc(ko)
# images: member path (relative to work/unp) -> new member bytes
import imgko
IMG = {}
spec = {}
for f in sorted(glob.glob('translation/images/*.json')):
    spec.update(json.load(open(f, encoding='utf-8')))
import hashlib, hgpt
HASH = json.load(open('work/imghash.json'))
KEY2H = {k: h for h, ks in HASH.items() for k in ks}
dups = {}
for key in spec:
    h = KEY2H.get(key)
    dups[key] = [k for k in HASH.get(h, []) if k != key] if h else []
for key, regions in spec.items():
    for k in [key] + dups.get(key, []):
        m, blk = k.rsplit('#', 1)
        if m in IMG:   # several blocks of one member
            tmp = 'work/unp/' + m
            orig = open(tmp, 'rb').read(); open(tmp, 'wb').write(IMG[m])
            try: IMG[m] = imgko.apply(m, int(blk), regions)[0]
            finally: open(tmp, 'wb').write(orig)
        else:
            IMG[m] = imgko.apply(m, int(blk), regions)[0]
IMG_SRC = {m: open('work/unp/' + m, 'rb').read() for m in IMG}
print('images patched', len(spec), 'members', len(IMG))
for m, data in IMG.items():
    if m.startswith('im/') and m.endswith('.zpt.dec'):
        changed['/PSP_GAME/USRDIR/' + m[:-4]] = har.write_zpt(data)

nhar = 0
for f in sorted(glob.glob(USR + '**/*.har', recursive=True)):
    d = open(f, 'rb').read()
    rel = f[len(USR):].replace('\\', '/')
    ver, ents = har.parse(d)
    new = {}
    for i, e in enumerate(ents):
        if e['name'].strip().endswith('.evs'):
            raw = har.data(e)
            nr = evs.build(raw, evs_repl)
            if nr != raw: new[i] = nr
        m = rel + '/' + e['name']
        # archives may hold several members with the same name: only replace the member whose
        # original bytes are exactly the ones the image patch was made from
        if m in IMG and har.data(e) == IMG_SRC[m]: new[i] = IMG[m]
    if new:
        changed['/PSP_GAME/USRDIR/' + rel] = har.build(d, new); nhar += 1
print('har rebuilt', nhar)

# EBOOT strings
D = bytearray(D0)
for off, ko in EKO.items():
    ja, room = EBOOT_SRC[off]
    b = enc(ko)
    old0 = len(re.sub(r'\{16[0-9A-F]{2}\}', 'xx', ja).encode('cp932'))
    room = min(room, ((off + old0 + 1 + 3) & ~3) - off - 1)   # zeros past the alignment padding may be data
    assert len(b) <= room, (off, ko)
    old = len(re.sub(r'\{16[0-9A-F]{2}\}', 'xx', ja).encode('cp932'))
    D[off:off + max(old, len(b)) + 1] = b + b'\0' * (max(old, len(b)) + 1 - len(b))

# ---------------------------------------------------------------- font
chars = set(hangul)
for t in texts + LEFT:
    chars |= set(t)
chars |= {chr(c) for r in ((0x20, 0x250), (0x370, 0x500), (0x2000, 0x2700), (0x3000, 0x3100), (0xff00, 0xfff0)) for c in range(*r)}
chars |= set('…‥・「」『』【】〈〉《》（）～♪☆★○●◎◇◆□■△▲▽▼※→←↑↓―‐ー、。！？＋－×÷＝≠＜＞％＆＊＠§°′″℃￥＄¢£')
# chars as the game sees them: translated kanji-slot codes are looked up as Hangul
chars = {c for c in chars if c not in '\n'}
os.makedirs('work/build', exist_ok=True)
nglyph, fsize = mkfont.build(sorted(chars), 'work/build/kfont.pgf')
font = open('work/build/kfont.pgf', 'rb').read()
print('font glyphs', nglyph, 'bytes', fsize)

# ---------------------------------------------------------------- ISO
out = sys.argv[1] if len(sys.argv) > 1 else 'work/kr.iso'
iso = isobuild.Iso(ISO, out)
lbn = iso.end // 2048
iso.add('/PSP_GAME/USRDIR', 'kfont.pgf;1', font)
path = b'disc0:/sce_lbn0x%x_size0x%x' % (lbn, len(font))
changed['/PSP_GAME/SYSDIR/EBOOT.BIN'] = ebootpatch.patch(bytes(D), S2H, path)
stat = {}
for p, data in sorted(changed.items()):
    r = iso.replace(p, data); stat[r] = stat.get(r, 0) + 1
iso.close()
print('iso', out, stat, 'bad chars', bad_chars)

# ---------------------------------------------------------------- structural verification (fails the build)
import verify, lencheck
if lencheck.run(fix) or verify.main(out):
    sys.exit('VERIFY FAILED: do not release this ISO')

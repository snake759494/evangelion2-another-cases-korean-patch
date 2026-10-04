"""Second pass: every NUL-delimited SJIS segment in .rodata/.data not yet covered (allows 0x16 xx icon codes)."""
import json, glob, re
D = open('work/eboot_plain.bin', 'rb').read()
covered = set()
for f in glob.glob('translation/batches/e*.json') + ['work/eboot_extra_done.json']:
    for item in json.load(open(f, encoding='utf-8')): covered.add(item[0])
real = json.load(open('work/eboot_real.json', encoding='utf-8'))
for x in real: covered.add(x['off'])
def decode(b):
    out = []; i = 0
    while i < len(b):
        c = b[i]
        if c == 0x16 and i + 1 < len(b): out.append('{16%02X}' % b[i+1]); i += 2; continue
        if c in (0x0a, 0x09) or 0x20 <= c < 0x7f: out.append(chr(c)); i += 1; continue
        if (0x81 <= c <= 0x9f or 0xe0 <= c <= 0xef) and i + 1 < len(b):
            try: out.append(b[i:i+2].decode('cp932')); i += 2; continue
            except UnicodeDecodeError: return None
        return None
    return ''.join(out)
KANA = re.compile('[ぁ-ヿ]')
JP = re.compile('[ぁ-ヿ一-鿿]')
res = []
p = 0x1b06c0
END = 0x253e7c
while p < END:
    if D[p] == 0: p += 1; continue
    e = D.index(b'\0', p)
    seg = D[p:e]
    t = decode(seg)
    if t is None:
        # data glued in front (e.g. a float): retry from aligned offsets
        for q2 in range((p + 3) & ~3, e, 4):
            t = decode(D[q2:e])
            if t: p = q2; break
    if t and p not in covered and len(JP.findall(t)) >= 2 and (KANA.search(t) or len(t) >= 2) and not re.search('[繝縺譁蜈]', t):
        q = e
        while q < len(D) and D[q] == 0: q += 1
        res.append([p, t, q - p - 1])
    p = e + 1
print(len(res), sum(len(x[1]) for x in res))
json.dump(res, open('work/eboot_extra.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
for x in res[:40]: print(hex(x[0]), x[2], x[1][:30])

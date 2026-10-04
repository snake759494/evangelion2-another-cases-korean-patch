"""List Japanese text segments still untouched in the built EBOOT (rodata+data)."""
import sys, os, re, json
sys.path.insert(0, os.path.dirname(__file__)); import verify, ebootstr2
O = open('work/eboot_plain.bin', 'rb').read()
N = verify.Reader(sys.argv[1] if len(sys.argv) > 1 else 'work/kr.iso').get('/PSP_GAME/SYSDIR/EBOOT.BIN')
KANA = re.compile('[ぁ-ヿ]'); KAN = re.compile('[一-鿿]')
out = []; p = 0x1b06c0
while p < 0x253e7c:
    if O[p] == 0: p += 1; continue
    e = O.index(b'\0', p)
    for q in [p] + list(range((p + 3) & ~3, e, 4)):
        t = ebootstr2.decode(O[q:e])
        if t: break
    if t and O[q:e] == N[q:e] and (KANA.search(t) or len(KAN.findall(t)) >= 2) and not re.search('[繝縺譁蜈]', t):
        z = e
        while z < len(O) and O[z] == 0: z += 1
        out.append([q, t, z - q - 1])
    p = e + 1
json.dump(out, open('work/eboot_left.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print(len(out))

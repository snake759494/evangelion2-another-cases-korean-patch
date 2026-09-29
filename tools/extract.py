"""Collect all translatable strings -> translation/unique_ja.json, batches."""
import sys, os, glob, json, struct
sys.path.insert(0, 'tools'); import textfmt, evs
U = {}   # jp -> id
order = []
def add(b):
    t = b.decode('cp932')
    if not any(ord(c) > 0x3000 or 0xff00 <= ord(c) for c in t): return
    if t not in U: U[t] = len(order); order.append(t)
def bind_blocks(d):
    cnt = struct.unpack_from('<H', d, 6)[0]; hs = struct.unpack_from('<I', d, 12)[0]
    sizes = struct.unpack_from('<%dI' % cnt, d, 0x10); p = hs
    for s in sizes:
        yield p, s; p += (s + 0x7ff) & ~0x7ff
# 1. imtext
d = open('work/unp/game/imtext.bin', 'rb').read()
for p, s in bind_blocks(d):
    for k, a, b, t in textfmt.parse(d[p:p+s])[0]:
        if t: add(t)
n1 = len(order)
# 2. evs
for f in sorted(glob.glob('work/unp/**/*.evs', recursive=True)):
    o, c = evs.parse(open(f, 'rb').read())
    for q, op, b in c:
        if op == 1: add(b[12:b.index(b'\0', 12)])
        elif op == 149: add(b[:b.index(b'\0')])
n2 = len(order)
# 3. free TEXT
for f in ('work/unp/free/f2info.bin', 'work/unp/free/f2tuto.bin'):
    for k, a, b, t in textfmt.parse(open(f, 'rb').read())[0]:
        if t: add(t)
print(n1, n2 - n1, len(order) - n2, sum(len(x) for x in order))
os.makedirs('translation/batches', exist_ok=True); os.makedirs('translation/out', exist_ok=True)
json.dump(order, open('translation/unique_ja.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
# batches by ~7000 chars, keep order (scene continuity)
b = []; cur = []; cl = 0
for i, t in enumerate(order):
    cur.append([i, t]); cl += len(t)
    if cl > 7000: b.append(cur); cur = []; cl = 0
if cur: b.append(cur)
for i, x in enumerate(b):
    json.dump(x, open('translation/batches/b%03d.json' % i, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
print('batches', len(b))

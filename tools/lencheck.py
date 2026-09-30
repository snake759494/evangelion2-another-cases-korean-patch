"""Per-source byte-length guard: no translation may exceed the longest original string of its source
(the game copies strings into buffers sized for the original data)."""
import sys, os, json, glob
sys.path.insert(0, os.path.dirname(__file__)); import bind, textfmt, evs
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def run(fix=None):
    U = json.load(open(os.path.join(ROOT, 'translation/unique_ja.json'), encoding='utf-8')); I = {u: i for i, u in enumerate(U)}
    KO = {}
    for f in glob.glob(os.path.join(ROOT, 'translation/out/b*.json')):
        for k, v in json.load(open(f, encoding='utf-8')).items(): KO[int(k)] = fix(v) if fix else v
    bl = lambda s: sum(1 if ord(c) < 0x80 else 2 for c in s)
    def texts(path):
        out = []
        for b in bind.parse(open(path, 'rb').read())[1]:
            if b[:4] == b'TEXT': out += [t.decode('cp932') for k, a, bb, t in textfmt.parse(b)[0] if t]
        return out
    src = {'imtext': texts(os.path.join(ROOT, 'work/unp/game/imtext.bin')), 'btimtext': texts(os.path.join(ROOT, 'work/unp/btl/btimtext.bin'))}
    E1, E149 = [], []
    for f in glob.glob(os.path.join(ROOT, 'work/unp/**/*.evs'), recursive=True):
        for p, op, b in evs.parse(open(f, 'rb').read())[1]:
            if op == 1: E1.append(b[12:b.index(b'\0', 12)].decode('cp932'))
            if op == 149: E149.append(b[:b.index(b'\0')].decode('cp932'))
    src['evs'] = E1; src['choice'] = E149
    for n in ('f2info', 'f2tuto'):
        src[n] = [t.decode('cp932') for k, a, b, t in textfmt.parse(open(os.path.join(ROOT, 'work/unp/free/%s.bin' % n), 'rb').read())[0] if t]
    bad = []
    for name, strs in src.items():
        strs = set(strs); o = max(len(s.encode('cp932')) for s in strs)
        n = 0
        for s in strs:
            i = I.get(s)
            if i is None or i not in KO: continue
            L = bl(KO[i]); n = max(n, L)
            if L > o: bad.append((name, i, L, o))
        print('%-9s strings %5d  orig max %4d  new max %4d' % (name, len(strs), o, n))
    for b in bad: print('  TOO LONG', b)
    return len(bad)
if __name__ == '__main__':
    sys.exit(1 if run() else 0)

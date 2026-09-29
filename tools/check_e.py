"""Validate EBOOT string translations translation/out/eNNN.json: {"off": "ko"}; byte limit = room."""
import sys, json, re, glob, os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(__file__)); import check
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FMT = re.compile(r'%[-+ #0-9.]*[a-zA-Z]|\$[a-z]|\{16[0-9A-F]{2}\}')
def blen(s):
    s = re.sub(r'\{16[0-9A-F]{2}\}', 'xx', s)
    return sum(1 if ord(c) < 0x80 else 2 for c in s)
def run(name):
    src = json.load(open(os.path.join(ROOT, 'translation/batches/%s.json' % name), encoding='utf8'))
    p = os.path.join(ROOT, 'translation/out/%s.json' % name)
    if not os.path.exists(p): print(name, '없음'); return len(src)
    out = json.load(open(p, encoding='utf8')); bad = 0
    for off, ja, room in src:
        ko = out.get(str(off)); e = []
        if ko is None: print(name, off, '누락'); bad += 1; continue
        if FMT.findall(ja) != FMT.findall(ko): e.append('서식코드 불일치 %s vs %s' % (FMT.findall(ja), FMT.findall(ko)))
        if blen(ko) > room: e.append('바이트 초과 %d>%d (한글·전각 2바이트, 반각 1바이트)' % (blen(ko), room))
        if ja.count('\n') < ko.count('\n'): e.append('줄 수 초과')
        for ch in re.sub(r'\{16[0-9A-F]{2}\}', '', ko):
            o = ord(ch)
            if 0xac00 <= o <= 0xd7a3 or 0x20 <= o < 0x7f or ch in check.SYM or ch in '\n\t': continue
            e.append('허용되지 않는 문자 %r' % ch); break
        if e: bad += 1; print(name, off, '|', repr(ja), '=>', repr(ko), '|', ' / '.join(e))
    print(name, '오류', bad, '/', len(src)); return bad
if __name__ == '__main__':
    names = sys.argv[1:]
    if names == ['all']: names = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'translation/batches/e*.json')))
    print('총 오류', sum(run(n) for n in names))

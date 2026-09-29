"""Validate translation/out/bNNN.json. usage: python tools/check.py b000 [b001 ...] | all"""
import sys, json, re, glob, os
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = {int(k): v for k, v in json.load(open(os.path.join(ROOT, 'work/jpn0_adv.json'))).items()}
SYM = set('…・「」『』（）()～~♪☆★○●◎◇◆□■△▲▽▼※→←↑↓、。！？!?,.:;：；/／-－+＋%％×=＝<>＜＞\'"“”‘’#＃&＆*＊[]［］【】《》〈〉 ―ー　0123456789')
CODE = re.compile(r'\$[a-z]|%\d*[a-z]|▽')
def width(s):
    w = 0
    for ch in s:
        o = ord(ch)
        if 0xac00 <= o <= 0xd7a3: w += 18
        else: w += W.get(o, 18)
    return w
def strip(s): return CODE.sub('', s)
def check(ja, ko):
    errs = []
    if sorted(CODE.findall(ja)) != sorted(CODE.findall(ko)):
        errs.append('제어코드 불일치 %s vs %s' % (CODE.findall(ja), CODE.findall(ko)))
    if ja.endswith('\n') != ko.endswith('\n'): errs.append('끝 줄바꿈 불일치')
    for ch in strip(ko).replace('\n', ''):
        o = ord(ch)
        if 0xac00 <= o <= 0xd7a3 or 0x20 <= o < 0x7f or ch in SYM: continue
        errs.append('허용되지 않는 문자 %r' % ch); break
    jl = ja.rstrip('\n').split('\n'); kl = ko.rstrip('\n').split('\n')
    dialog = len(jl) >= 2 or len(ja) > 12
    maxl = len(jl) + (1 if dialog and len(jl) < 3 else 0)
    if len(kl) > maxl: errs.append('줄 수 초과 %d>%d' % (len(kl), maxl))
    ow = max(width(strip(l)) for l in jl)
    lim = max(ow, 306) if dialog else max(ow + 18, 36)
    for k, l in enumerate(kl):
        w = width(strip(l))
        if w > lim: errs.append('%d번째 줄 폭 초과 %dpx>%dpx (%s)' % (k + 1, w, lim, l))
    return errs
def run(name):
    src = json.load(open(os.path.join(ROOT, 'translation/batches/%s.json' % name), encoding='utf8'))
    p = os.path.join(ROOT, 'translation/out/%s.json' % name)
    if not os.path.exists(p): print(name, '없음'); return len(src)
    out = json.load(open(p, encoding='utf8')); bad = 0
    for i, ja in src:
        ko = out.get(str(i))
        if ko is None: print(name, i, '누락'); bad += 1; continue
        e = check(ja, ko)
        if e: bad += 1; print(name, i, '|', repr(ja), '=>', repr(ko), '|', ' / '.join(e))
    print(name, '오류', bad, '/', len(src)); return bad
if __name__ == '__main__':
    names = sys.argv[1:]
    if names == ['all']: names = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(ROOT, 'translation/batches/b*.json')))
    tot = sum(run(n) for n in names); print('총 오류', tot)

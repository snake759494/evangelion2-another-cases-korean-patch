import os, re, sys, collections, json
pat = re.compile(rb'(?:[\x81-\x9f\xe0-\xea][\x40-\x7e\x80-\xfc]|[\x20-\x7e\x0a]){4,}')
def jp(b):
    try: s = b.decode('cp932')
    except: return None
    n = sum(1 for ch in s if ord(ch) > 0x3000)
    return s if n >= 2 else None
res = collections.Counter(); files = {}
for root, ds, fs in os.walk('work/unp'):
    for f in fs:
        p = os.path.join(root, f).replace(chr(92), '/')
        d = open(p, 'rb').read()
        cnt = 0; tot = 0
        for m in pat.finditer(d):
            s = jp(m.group())
            if s: cnt += 1; tot += len(s)
        if cnt:
            ext = p.rsplit('.', 1)[-1].strip()
            res[ext] += tot; files[p] = (cnt, tot)
print(res)
json.dump(files, open('work/sjfiles.json', 'w'), indent=0)
top = sorted(files.items(), key=lambda x: -x[1][1])[:40]
for k, v in top: print(v, k)

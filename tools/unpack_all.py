import sys, os, glob, collections
sys.path.insert(0, 'tools'); import har
R = 'work/iso/PSP_GAME/USRDIR/'
out = 'work/unp/'
mag = collections.Counter()
for f in sorted(glob.glob(R + '**/*', recursive=True)):
    if os.path.isdir(f): continue
    rel = f[len(R):].replace(chr(92), '/')
    d = open(f, 'rb').read()
    items = []
    if d[:4] == b'HGAR':
        for e in har.parse(d)[1]:
            items.append((rel + '/' + e['name'], har.data(e)))
    elif rel.endswith('.zpt'):
        items.append((rel + '.dec', har.read_zpt(d)))
    else:
        items.append((rel, d))
    for n, b in items:
        p = out + n; os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(b)
        mag[(b[:4], n.rsplit('.', 1)[-1])] += 1
for k, v in sorted(mag.items(), key=lambda x: -x[1]): print(v, k)

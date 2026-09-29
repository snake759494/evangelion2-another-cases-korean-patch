import sys, os, glob, hashlib, json
sys.path.insert(0, 'tools'); import hgpt
from PIL import Image
dirs = sys.argv[1:]
seen = {}; index = []
for dd in dirs:
    for f in sorted(glob.glob('work/unp/' + dd + '/**/*', recursive=True)):
        if os.path.isdir(f) or not (f.endswith('.hpt') or f.endswith('.dec') or f.endswith('.zpt') or f.endswith('.zmt')): continue
        d = open(f, 'rb').read()
        if d[:4] != b'HGPT': continue
        for k, b in enumerate(hgpt.blocks(d)):
            if b['w'] == 0 or b['w'] > 1024 or b['h'] > 1024: continue
            try: im, s = hgpt.image(d, b)
            except Exception as e: continue
            h = hashlib.md5(im.tobytes()).hexdigest()
            rel = f[len('work/unp/'):].replace(chr(92), '/')
            if h in seen: seen[h]['dups'].append([rel, k]); continue
            p = 'work/img/%s_%d.png' % (rel.replace('/', '__').replace(' ', ''), k)
            os.makedirs('work/img', exist_ok=True); im.save(p)
            seen[h] = dict(src=rel, blk=k, png=p, w=b['w'], h=b['h'], swz=s, dups=[])
json.dump(list(seen.values()), open('work/img_index_%s.json' % '_'.join(x.replace('/', '-') for x in dirs), 'w'), indent=0)
print(len(seen))

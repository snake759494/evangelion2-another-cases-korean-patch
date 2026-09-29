"""Hash every HGPT block in work/unp -> work/imghash.json {md5: ["member#blk", ...]} (decoded RGBA content)."""
import sys, os, glob, json, hashlib
sys.path.insert(0, os.path.dirname(__file__)); import hgpt
out = {}
for f in glob.glob('work/unp/**/*', recursive=True):
    if os.path.isdir(f): continue
    with open(f, 'rb') as fh:
        if fh.read(4) != b'HGPT': continue
    d = open(f, 'rb').read(); rel = f[9:].replace(chr(92), '/')
    for k, b in enumerate(hgpt.blocks(d)):
        if not (0 < b['w'] <= 1024 and 0 < b['h'] <= 1024): continue
        try: im, s = hgpt.image(d, b)
        except Exception: continue
        out.setdefault(hashlib.md5(im.tobytes()).hexdigest(), []).append('%s#%d' % (rel, k))
json.dump(out, open('work/imghash.json', 'w'))
print(len(out), sum(len(v) for v in out.values()))

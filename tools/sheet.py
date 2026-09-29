import sys, json
from PIL import Image, ImageDraw
I = json.load(open(sys.argv[1])); pre = sys.argv[2]; flt = sys.argv[3] if len(sys.argv) > 3 else ''
I = [x for x in I if flt in x['src']]
TW, TH, C, R = 300, 170, 4, 5
for s in range(0, len(I), C*R):
    sh = Image.new('RGB', (TW*C, (TH+14)*R), (60, 60, 60)); dr = ImageDraw.Draw(sh)
    for j, x in enumerate(I[s:s+C*R]):
        im = Image.open(x['png']).convert('RGBA'); im.thumbnail((TW-4, TH-4))
        bg = Image.new('RGBA', im.size, (40, 40, 90, 255)); bg.alpha_composite(im)
        cx, cy = (j % C)*TW, (j//C)*(TH+14)
        sh.paste(bg.convert('RGB'), (cx+2, cy+2))
        dr.text((cx+2, cy+TH), '%d %s' % (s+j, x['src'][-26:]), fill=(255, 255, 0))
    sh.save('%s_%02d.png' % (pre, s//(C*R)))
print(len(I))

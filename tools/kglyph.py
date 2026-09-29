from PIL import Image, ImageDraw, ImageFont
FONT = 'NanumSquareNeo-cBd.ttf'
SIZE = 17
_f = {}
def font(path=FONT, size=SIZE):
    if (path, size) not in _f: _f[(path, size)] = ImageFont.truetype(path, size)
    return _f[(path, size)]
def render(ch, path=FONT, size=SIZE, asc=15, adv=18):
    """returns dict(bmp, left, top, adv) with baseline-based metrics (px)."""
    f = font(path, size)
    W = 40
    im = Image.new('L', (W, W), 0)
    d = ImageDraw.Draw(im)
    base = 28
    d.text((4, base), ch, font=f, fill=255, anchor='ls')
    bb = im.getbbox()
    if not bb: return dict(bmp=[[0]], left=0, top=0, adv=int(f.getlength(ch) * 64))
    x0, y0, x1, y1 = bb
    bmp = [[im.getpixel((x, y)) * 15 // 255 for x in range(x0, x1)] for y in range(y0, y1)]
    return dict(bmp=bmp, left=x0 - 4, top=base - y0, adv=int(round(f.getlength(ch))) * 64)

"""Build game/kfont.pgf: Hangul from NanumSquareNeo Bold, everything else copied from jpn0.pgf."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pgf, kglyph
JPN0 = 'D:/psp/ppsspp_win/assets/flash0/font/jpn0.pgf'
def build(chars, out):
    P = pgf.PGF(open(JPN0, 'rb').read())
    gl = {}
    base = set(chr(c) for c in range(0x20, 0x7f))
    for ch in sorted(set(chars) | base):
        c = ord(ch)
        if 0xac00 <= c <= 0xd7a3:
            g = kglyph.render(ch)
            g['left'] += 1; g['adv'] = 18 * 64
            g['top'] += 3   # game clips below baseline+1 (cell = 17 - top .. 18)
            gl[c] = g
        else:
            i = P.index(c)
            if i is None: continue
            g = P.glyph(i)
            gl[c] = dict(bmp=g['bmp'], left=g['left'], top=g['top'], adv=g['adv'][0])
    data = pgf.write(gl, P)
    open(out, 'wb').write(data)
    return len(gl), len(data)
if __name__ == '__main__':
    ks = [bytes([hi, lo]).decode('cp949') for hi in range(0xb0, 0xc9) for lo in range(0xa1, 0xff)]
    extra = ''.join(chr(c) for c in list(range(0x3000, 0x3100)) + list(range(0xff01, 0xff5f)) + list(range(0x2010, 0x2270)) + list(range(0x25a0, 0x2670)))
    print(build(ks + list(extra), 'work/kfont.pgf'))

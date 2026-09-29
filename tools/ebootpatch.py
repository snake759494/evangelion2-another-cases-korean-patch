"""EBOOT patches.
1) Font: sceFontOpen(lib, FindOptimumFont(...)) -> sceFontOpenUserFile(lib, FONT_PATH, mode, &err)
   - path string replaces debug alloc labels "Font Header/Font Char Buffer/FontLinkTex" (44 bytes)
   - a1 computed PC-relative (bal) so no relocation is needed; the jal FindOptimumFont reloc is disabled.
2) SJIS -> Unicode table remap (kanji slots -> Hangul).
"""
import struct
SEG1 = 0x1daa80
RANGE = SEG1 + 0x5485c
UTAB = SEG1 + 0x51160
TXT = 0x80
FONT_PATH = b'disc0:/PSP_GAME/USRDIR/kfont.pgf'
PATH_OFF = 0x2534c4          # file offset in .data ('host0:../../cdimg/' debug buffer, 132 bytes)
NID_OPEN, NID_OPENUSERFILE = 0xA834319D, 0x57FCB733

def w32(D, off, v, expect=None):
    if expect is not None:
        cur = struct.unpack_from('<I', D, off)[0]
        assert cur == expect, (hex(off), hex(cur), hex(expect))
    struct.pack_into('<I', D, off, v)

def ranges(D):
    return [struct.unpack_from('<HH', D, RANGE + 4*i) for i in range(90)]

def index_of(rng, c):
    best = None
    for a, b in rng:
        if a <= c: best = (a, b)
    return c - best[0] + best[1]

def kanji_slots():
    out = []
    for hi in list(range(0x88, 0xa0)) + list(range(0xe0, 0xeb)):
        for lo in list(range(0x40, 0x7f)) + list(range(0x80, 0xfd)):
            c = hi << 8 | lo
            if c < 0x889f: continue
            try: bytes([hi, lo]).decode('cp932')
            except UnicodeDecodeError: continue
            out.append(c)
    return out

def patch(D, mapping, font_path=FONT_PATH):
    D = bytearray(D)
    # --- font path
    assert D[PATH_OFF:PATH_OFF+18] == b'host0:../../cdimg/'
    assert len(font_path) < 100
    D[PATH_OFF:PATH_OFF+100] = font_path.ljust(100, b'\0')
    str_v = PATH_OFF - SEG1 + 0x1daa00
    ra = 0x652c8
    delta = str_v - ra
    hi = (delta + 0x8000) >> 16; lo = (delta - (hi << 16)) & 0xffff
    w32(D, TXT+0x652c0, 0x04110001, 0x03a02821)          # bal +8        (was move a1,sp)
    w32(D, TXT+0x652c4, 0x00000000, 0x27a600b0)          # nop
    w32(D, TXT+0x652c8, 0x3c050000 | hi, 0xe7a10000)     # lui a1,hi
    w32(D, TXT+0x652d0, 0x24a50000 | lo, 0xa7a9001a)     # addiu a1,a1,lo
    w32(D, TXT+0x652d4, 0x00bf2821, 0xa7a80016)          # addu a1,a1,ra
    w32(D, TXT+0x652d8, 0x00000000)                      # nop (was jal FindOptimumFont)
    w32(D, TXT+0x652dc, 0x00000000, 0xa7a70014)          # nop
    w32(D, TXT+0x652fc, 0x00000000, 0x00402821)          # nop (was move a1,v0)
    # disable R_MIPS_26 reloc of the removed jal
    import elf
    for eo, v, t, ob, ab in elf.relocs():
        if v == 0x652d8:
            assert t == 4; D[eo+4] = 0
    # NID swap
    nid = struct.pack('<I', NID_OPEN)
    i = D.find(nid, 0x1af0b0, 0x1af0b0 + 0x294); assert i > 0 and D.find(nid, i+1, 0x1af0b0+0x294) < 0
    D[i:i+4] = struct.pack('<I', NID_OPENUSERFILE)
    # --- SJIS->Unicode
    rng = ranges(D)
    for c, u in mapping.items():
        struct.pack_into('<H', D, UTAB + 2*index_of(rng, c), ord(u))
    return bytes(D)

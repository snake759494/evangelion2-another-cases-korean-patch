"""BIND container: 'BIND', u16 ver, u16 count, u32 align, u32 header_size, size[count]; blocks aligned.
ver 2 (btl/btimtext.bin): u16 sizes.  ver 4 (game/imtext.bin): u32 sizes."""
import struct

def _fmt(ver):
    if ver == 2: return 'H'
    if ver == 4: return 'I'
    raise ValueError('unknown BIND version %d' % ver)

def parse(d):
    assert d[:4] == b'BIND', d[:4]
    ver, cnt = struct.unpack_from('<HH', d, 4); al, hs = struct.unpack_from('<II', d, 8)
    f = _fmt(ver)
    sizes = struct.unpack_from('<%d%s' % (cnt, f), d, 0x10); p = hs; out = []
    for s in sizes:
        assert p + s <= len(d), 'BIND block past end'
        out.append(d[p:p+s]); p += (s + al - 1) // al * al
    assert p == len(d), ('BIND size mismatch', p, len(d))
    return (ver, al, hs, d[:hs]), out

def build(meta, blocks):
    ver, al, hs, hdr = meta
    f = _fmt(ver)
    h = bytearray(hdr)
    for i, b in enumerate(blocks):
        if f == 'H': assert len(b) < 0x10000, 'block too large for u16 size table'
        struct.pack_into('<' + f, h, 0x10 + struct.calcsize(f) * i, len(b))
    out = bytearray(h)
    for b in blocks:
        out += b; out += b'\0' * ((-len(out)) % al)
    return bytes(out)

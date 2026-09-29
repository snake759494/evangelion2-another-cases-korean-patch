"""BIND container: 'BIND', u16 ver, u16 count, u32 align, u32 header_size, u32 size[count]; blocks aligned."""
import struct
def parse(d):
    ver, cnt = struct.unpack_from('<HH', d, 4); al, hs = struct.unpack_from('<II', d, 8)
    sizes = struct.unpack_from('<%dI' % cnt, d, 0x10); p = hs; out = []
    for s in sizes:
        out.append(d[p:p+s]); p += (s + al - 1) // al * al
    return (ver, al, hs, d[:hs]), out
def build(meta, blocks):
    ver, al, hs, hdr = meta
    h = bytearray(hdr)
    for i, b in enumerate(blocks): struct.pack_into('<I', h, 0x10 + 4*i, len(b))
    out = bytearray(h)
    for b in blocks:
        out += b; out += b'\0' * ((-len(out)) % al)
    return bytes(out)

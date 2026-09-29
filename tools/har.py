"""HGAR (.har) archive + zpt (u32 raw size + raw deflate)."""
import struct, zlib

def inflate(b):
    return zlib.decompressobj(-15).decompress(b)

def deflate(b):
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return c.compress(b) + c.flush()

def read_zpt(d):
    n = struct.unpack_from('<I', d)[0]
    o = inflate(d[4:]); assert len(o) == n
    return o

def write_zpt(raw):
    return struct.pack('<I', len(raw)) + deflate(raw)

def parse(d):
    assert d[:4] == b'HGAR', d[:4]
    ver, cnt = struct.unpack_from('<HH', d, 4)
    offs = struct.unpack_from('<%dI' % cnt, d, 8)
    ents = []
    for i, p in enumerate(offs):
        end = offs[i+1] if i+1 < cnt else len(d)
        name = d[p:p+12].split(b'\0')[0].decode('ascii', 'replace')
        flag, sz = struct.unpack_from('<II', d, p+12)
        body = d[p+20:p+20+sz]
        ents.append(dict(name=name, flag=flag, raw=body, pad=d[p+20+sz:end]))
    return ver, ents

def data(e):
    if e['flag'] & 0x80000000:
        return read_zpt(e['raw'])
    return e['raw']

def build(d, newdata):
    """newdata: {index: raw bytes} replaces member data (recompressed when flagged)."""
    ver, cnt = struct.unpack_from('<HH', d, 4)
    offs = struct.unpack_from('<%dI' % cnt, d, 8)
    out = bytearray(d[:offs[0]])
    _, ents = parse(d)
    for i, e in enumerate(ents):
        struct.pack_into('<I', out, 8 + 4*i, len(out))
        p = offs[i]
        body = e['raw']
        if i in newdata:
            body = write_zpt(newdata[i]) if e['flag'] & 0x80000000 else newdata[i]
        out += d[p:p+12] + struct.pack('<II', e['flag'], len(body)) + body
        out += b'\0' * ((-len(out)) % 4)
    return bytes(out)

"""TEXT block: 'TEXT', n, tab_off, data_off, (key,off)*n ; record = u32 a, u32 b, SJIS string NUL, pad4."""
import struct
def parse(d):
    assert d[:4] == b'TEXT'
    n, to, do = struct.unpack_from('<III', d, 4)
    ents = [struct.unpack_from('<II', d, to + 8*i) for i in range(n)]
    recs = []
    for k, o in ents:
        if o + 8 > len(d) or o < do:
            recs.append((k, None, None, None)); continue
        a, b = struct.unpack_from('<II', d, o)
        e = d.index(b'\0', o + 8)
        recs.append((k, a, b, d[o+8:e]))
    return recs, (n, to, do)

def build(d, repl):
    """rebuild TEXT block d; repl(bytes)->bytes for each record string. Keys sharing a record stay shared."""
    recs, (n, to, do) = parse(d)
    ents = [struct.unpack_from('<II', d, to + 8*i) for i in range(n)]
    out = bytearray(d[:do])
    newoff = {}
    # records in original order of offsets
    for o in sorted(set(o for k, o in ents if do <= o < len(d))):
        a, b = struct.unpack_from('<II', d, o)
        e = d.index(b'\0', o + 8)
        s = repl(d[o+8:e])
        newoff[o] = len(out)
        out += struct.pack('<II', a, b) + s + b'\0'
        while len(out) % 4: out += b'\0'
    # tail after last record (if any) is dropped only if it was padding
    for i, (k, o) in enumerate(ents):
        struct.pack_into('<II', out, to + 8*i, k, newoff.get(o, len(out) if o >= len(d) else o))
    return bytes(out)

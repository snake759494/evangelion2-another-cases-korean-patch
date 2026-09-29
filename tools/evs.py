import struct
def parse(d):
    assert d[:4] == b'.EVS'
    n = struct.unpack_from('<I', d, 4)[0]
    offs = list(struct.unpack_from('<%dI' % n, d, 8))
    cmds = []
    p = 8 + 4*n
    while p < len(d):
        op, ln = struct.unpack_from('<HH', d, p)
        body = d[p+4:p+4+ln]
        cmds.append((p, op, body))
        p += 4 + ((ln + 3) & ~3)
    return offs, cmds

def build(d, repl):
    """repl(op, bytes)->bytes|None for op1 text / op149 choices. Offsets table remapped."""
    offs, cmds = parse(d)
    n = len(offs)
    out = bytearray(d[:8 + 4*n])
    remap = {}
    for p, op, body in cmds:
        remap[p] = len(out)
        if op == 1:
            e = body.index(b'\0', 12)
            s = repl(1, body[12:e])
            if s is not None: body = body[:12] + s + b'\0' + body[e+1:]
        elif op == 149:
            e = body.index(b'\0')
            s = repl(149, body[:e])
            if s is not None: body = s + b'\0' + body[e+1:]
        ln = len(body); assert ln < 0x10000
        out += struct.pack('<HH', op, ln) + body + b'\0' * ((-ln) % 4)
    remap[len(d)] = len(out)
    for i, o in enumerate(offs):
        struct.pack_into('<I', out, 8 + 4*i, remap[o])
    return bytes(out)

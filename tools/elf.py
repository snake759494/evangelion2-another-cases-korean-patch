import struct
D = open(__import__('os').path.join(__import__('os').path.dirname(__file__), '..', 'work', 'eboot_plain.bin'), 'rb').read()
e_phoff = struct.unpack_from('<I', D, 0x1c)[0]
ph = [struct.unpack_from('<8I', D, e_phoff + 32*i) for i in range(struct.unpack_from('<H', D, 0x2c)[0])]
SEGS = [(p[2], p[1], p[4]) for p in ph if p[0] == 1]  # vaddr, off, filesz
def v2o(v):
    for va, off, sz in SEGS:
        if va <= v < va + sz: return v - va + off
def u32(v): return struct.unpack_from('<I', D, v2o(v))[0]
def cstr(v):
    o = v2o(v); return D[o:D.index(b'\0', o)].decode('latin1')
def imports():
    # module info: paddr of first PH
    mi = ph[0][3] & 0x7fffffff
    mo = ph[0][3]
    stub, stub_end = struct.unpack_from('<II', D, mo + 0x2c)
    res = {}
    v = stub
    while v < stub_end:
        name, ver, attr, esz, nvar, nfunc, nids, funcs = struct.unpack_from('<IHHBBHII', D, v2o(v))
        lib = cstr(name) if name else '?'
        for i in range(nfunc):
            res[funcs + 8*i] = (lib, u32(nids + 4*i))
        v += esz * 4
    return res
if __name__ == '__main__':
    print([tuple(map(hex,x)) for x in SEGS])
    for a, (l, n) in sorted(imports().items()):
        if 'Font' in l or 'Utility' in l or 'sceCcc' in l.lower(): print(hex(a), l, hex(n))

def relocs():
    """yield (file_offset_of_entry, target_vaddr, type, ofsbase, addrbase)"""
    shoff = struct.unpack_from('<I', D, 0x20)[0]; shn = struct.unpack_from('<H', D, 0x30)[0]
    for i in range(shn):
        s = struct.unpack_from('<10I', D, shoff + 40*i)
        if s[1] != 0x700000a0: continue
        for k in range(s[5] // 8):
            eo = s[4] + 8*k
            off, info = struct.unpack_from('<II', D, eo)
            ob = (info >> 8) & 0xff
            yield eo, SEGS[ob][0] + off, info & 0xff, ob, (info >> 16) & 0xff

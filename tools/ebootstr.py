"""Find SJIS strings in EBOOT that are referenced by relocations (pointers / lui+addiu)."""
import sys, os, struct, re, json
sys.path.insert(0, os.path.dirname(__file__)); import elf
D = elf.D
def v2o(seg, v): return elf.SEGS[seg][1] + v  # addr relative to seg base
def targets():
    """map target file offset -> list of (kind, reloc entry offset / insn offset)"""
    T = {}
    hi = {}
    R = list(elf.relocs())
    pend = []
    for eo, v, t, ob, ab in R:
        o = elf.v2o(v)
        if o is None: continue
        w = struct.unpack_from('<I', D, o)[0]
        if t == 2:
            tgt = elf.SEGS[ab][1] + w
            T.setdefault(tgt, []).append(('ptr', o, ab))
        elif t == 5:
            pend.append((o, w, ab))
        elif t == 6:
            lo = w & 0xffff; lo = lo - 0x10000 if lo & 0x8000 else lo
            for ho, hw, hab in pend[-4:]:
                tgt = elf.SEGS[ab][1] + ((hw & 0xffff) << 16) + lo
                T.setdefault(tgt, []).append(('hilo', ho, o, ab))
                break
            # keep pend (HI may pair with several LO)
    return T
if __name__ == '__main__':
    T = targets()
    pat = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\x7e\x80-\xfc]|[\x20-\x7e\x0a\x09])+\x00')
    out = []
    for m in pat.finditer(D, 0x1b06c0, 0x253e7c):
        s = m.group()[:-1]
        try: t = s.decode('cp932')
        except UnicodeDecodeError: continue
        if not any(ord(c) >= 0x3000 for c in t): continue
        st = m.start()
        # also allow substring start (strings may share tails); find referenced start inside
        refs = T.get(st)
        # space until next non-zero byte
        e = m.end()
        while e < len(D) and D[e] == 0: e += 1
        out.append(dict(off=st, ja=t, ref=len(refs) if refs else 0, room=e - st - 1))
    print(len(out), sum(1 for x in out if x['ref']))
    json.dump(out, open('work/eboot_strings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    for x in out[:10]: print(x)
    un = [x for x in out if not x['ref']]
    for x in un[:30]: print('UNREF', hex(x['off']), x['ja'][:30])

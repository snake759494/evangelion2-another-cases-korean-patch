"""Decompressor/compressor for the 9-bit context-table LZ used by the game (EBOOT 0x14338)."""
def decompress(src, usize):
    out = bytearray(); tab = [[0]*32 for _ in range(256)]; cnt = [0]*256
    ctx = 0; pos = 0; bit = 0
    while len(out) < usize:
        t = ((src[pos] | (src[pos+1] << 8 if pos+1 < len(src) else 0)) >> bit) & 0x1ff
        pos += 1; bit += 1
        if bit == 8: bit = 0; pos += 1
        start = len(out)
        if t & 0x100: out.append(t & 0xff)
        else:
            p = tab[ctx][t >> 3]
            for k in range((t & 7) + 1): out.append(out[p+k])
        tab[ctx][cnt[ctx]] = start; cnt[ctx] = (cnt[ctx] + 1) & 31
        ctx = out[-1]
    return bytes(out[:usize])

def compress(data):
    # the game does not clear the position table between files: never use unwritten slots
    tab = [[-1]*32 for _ in range(256)]; cnt = [0]*256
    toks = []; ctx = 0; i = 0; n = len(data)
    while i < n:
        best = 0; bs = 0
        row = tab[ctx]
        for s in range(32):
            p = row[s]
            if p < 0 or p >= i: continue
            L = 0
            while L < 8 and i+L < n and data[p+L] == data[i+L]: L += 1
            if L > best: best, bs = L, s
            if L == 8: break
        if best >= 2:
            toks.append((bs << 3) | (best - 1)); ln = best
        else:
            toks.append(0x100 | data[i]); ln = 1
        row[cnt[ctx]] = i; cnt[ctx] = (cnt[ctx] + 1) & 31
        i += ln; ctx = data[i-1]
    acc = 0; nb = 0; out = bytearray()
    for t in toks:
        acc |= t << nb; nb += 9
        while nb >= 8: out.append(acc & 0xff); acc >>= 8; nb -= 8
    if nb: out.append(acc & 0xff)
    out += b'\0\0'
    return bytes(out)

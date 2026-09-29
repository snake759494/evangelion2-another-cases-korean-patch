def unswizzle(data, width_bytes, height):
    out = bytearray(len(data)); bw = width_bytes // 16; i = 0
    for by in range(0, height, 8):
        for bx in range(bw):
            for r in range(8):
                dst = (by + r) * width_bytes + bx * 16
                out[dst:dst+16] = data[i:i+16]; i += 16
    return bytes(out)
def swizzle(data, width_bytes, height):
    out = bytearray(len(data)); bw = width_bytes // 16; i = 0
    for by in range(0, height, 8):
        for bx in range(bw):
            for r in range(8):
                src = (by + r) * width_bytes + bx * 16
                out[i:i+16] = data[src:src+16]; i += 16
    return bytes(out)

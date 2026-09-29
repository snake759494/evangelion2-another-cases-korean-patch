"""Minimal in-place ISO9660 patcher for the PSP image.

* replace(): a file that still fits in its sectors is rewritten in place,
  otherwise it is appended at the end of the image and its directory record
  (LE/BE extent + size) is updated.
* add(): inserts a new directory record (sorted) into an existing directory
  sector that has room, the data is appended at the end.
The PVD volume space size is updated at the end.  No Joliet/RR/UDF on this disc.
"""
import struct, shutil, os

SEC = 2048


class Iso:
    def __init__(self, src, dst):
        shutil.copyfile(src, dst)
        self.f = open(dst, 'r+b')
        self.f.seek(0, 2)
        self.end = self.f.tell()
        assert self.end % SEC == 0

    # ---- directory helpers
    def _read_dir(self, lba, ln):
        self.f.seek(lba * SEC)
        return bytearray(self.f.read(ln))

    def _root(self):
        self.f.seek(16 * SEC)
        pvd = self.f.read(SEC)
        rec = pvd[156:156 + 34]
        return struct.unpack('<I', rec[2:6])[0], struct.unpack('<I', rec[10:14])[0]

    def _iter(self, data):
        off = 0
        while off < len(data):
            rl = data[off]
            if rl == 0:
                off = (off // SEC + 1) * SEC
                continue
            nlen = data[off + 32]
            name = data[off + 33:off + 33 + nlen].decode('latin-1').split(';')[0]
            yield off, rl, name
            off += rl

    def find(self, path):
        """returns (dir_lba, dir_len, rec_offset_in_dir, lba, size)"""
        lba, ln = self._root()
        parts = [p for p in path.strip('/').split('/') if p]
        for i, part in enumerate(parts):
            data = self._read_dir(lba, ln)
            for off, rl, name in self._iter(data):
                if name.upper() == part.upper():
                    rec = data[off:off + rl]
                    clba = struct.unpack('<I', rec[2:6])[0]
                    cln = struct.unpack('<I', rec[10:14])[0]
                    if i == len(parts) - 1:
                        return lba, ln, off, clba, cln
                    lba, ln = clba, cln
                    break
            else:
                raise FileNotFoundError(path)

    def _set_rec(self, dir_lba, rec_off, lba, size):
        self.f.seek(dir_lba * SEC + rec_off + 2)
        self.f.write(struct.pack('<I', lba) + struct.pack('>I', lba))
        self.f.seek(dir_lba * SEC + rec_off + 10)
        self.f.write(struct.pack('<I', size) + struct.pack('>I', size))

    def _append(self, data):
        lba = self.end // SEC
        self.f.seek(self.end)
        self.f.write(data)
        pad = (-len(data)) % SEC
        self.f.write(b'\0' * pad)
        self.end += len(data) + pad
        return lba

    def read(self, path):
        _, _, _, lba, size = self.find(path)
        self.f.seek(lba * SEC)
        return self.f.read(size)

    def replace(self, path, data):
        dlba, dln, roff, lba, size = self.find(path)
        if (len(data) + SEC - 1) // SEC <= (size + SEC - 1) // SEC:
            self.f.seek(lba * SEC)
            self.f.write(data)
            self.f.write(b'\0' * ((-len(data)) % SEC))
            self._set_rec(dlba, roff, lba, len(data))
            return 'inplace'
        nl = self._append(data)
        self._set_rec(dlba, roff, nl, len(data))
        return 'appended'

    def add(self, dirpath, name, data):
        _, _, _, dlba, dln = self.find(dirpath)
        d = self._read_dir(dlba, dln)
        recs = []
        used = 0
        for off, rl, nm in self._iter(d):
            recs.append(bytes(d[off:off + rl]))
        assert dln == SEC, 'multi-sector directory not supported'
        template = recs[-1]
        nb = name.encode('ascii')
        rl = 33 + len(nb)
        rl += rl & 1
        new = bytearray(template[:33]) + nb + (b'\0' if (33 + len(nb)) & 1 else b'')
        new[0] = rl
        new[32] = len(nb)
        lba = self._append(data)
        struct.pack_into('<I', new, 2, lba); struct.pack_into('>I', new, 6, lba)
        struct.pack_into('<I', new, 10, len(data)); struct.pack_into('>I', new, 14, len(data))
        new[25] = 0  # file flags: regular file
        # sorted insertion after . and ..
        fixed, rest = recs[:2], recs[2:]
        rest.append(bytes(new))
        rest.sort(key=lambda r: r[33:33 + r[32]])
        blob = b''.join(fixed + rest)
        assert len(blob) <= SEC, 'directory full'
        self.f.seek(dlba * SEC)
        self.f.write(blob + b'\0' * (SEC - len(blob)))

    def close(self):
        tot = self.end // SEC
        self.f.seek(16 * SEC + 80)
        self.f.write(struct.pack('<I', tot) + struct.pack('>I', tot))
        self.f.close()

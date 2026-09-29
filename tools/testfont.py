import sys; sys.path.insert(0, 'tools')
import ebootpatch as E, isobuild
D = open('work/eboot_plain.bin', 'rb').read()
ks = [bytes([hi, lo]).decode('cp949') for hi in range(0xb0, 0xc9) for lo in range(0xa1, 0xff)]
sl = E.kanji_slots()
m = {c: ks[i] for i, c in enumerate(sl[:len(ks)])}
iso = isobuild.Iso('Shin Seiki Evangelion 2 - Tsukurareshi Sekai - Another Cases (Japan).iso', 'work/test.iso')
font = open('work/kfont.pgf', 'rb').read()
lbn = iso.end // 2048
iso.add('/PSP_GAME/USRDIR', 'kfont.pgf;1', font)
path = b'disc0:/sce_lbn0x%x_size0x%x' % (lbn, len(font))
print(path, iso.find('/PSP_GAME/USRDIR/kfont.pgf'))
P = E.patch(D, m, path)
print(iso.replace('/PSP_GAME/SYSDIR/EBOOT.BIN', P))
iso.close()

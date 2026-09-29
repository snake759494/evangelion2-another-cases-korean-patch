import capstone,struct,sys,os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D=open(os.path.join(ROOT,'work','eboot_plain.bin'),'rb').read()
OFF=0x80
md=capstone.Cs(capstone.CS_ARCH_MIPS,capstone.CS_MODE_MIPS32+capstone.CS_MODE_LITTLE_ENDIAN); md.skipdata=True
def dis(v,n):
    for i in md.disasm(D[v+OFF:v+OFF+4*n],v): print('%06x: %s %s'%(i.address,i.mnemonic,i.op_str))
def jal_to(target):
    w=(0x0C000000|(target>>2)); return [p-OFF for p in range(OFF,len(D)-4,4) if struct.unpack_from('<I',D,p)[0]==w]
if __name__=='__main__': dis(int(sys.argv[1],16),int(sys.argv[2]))

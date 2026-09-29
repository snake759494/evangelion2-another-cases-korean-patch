"""dig member container: N x 24B entries (id, size, off, 0, type, 0); header size = first entry's offset."""
import struct
def members(d):
    out=[]; hdr=struct.unpack_from('<I',d,8)[0]; p=0
    while p<hdr:
        i,s,o,z,t,z2=struct.unpack_from('<6I',d,p)
        out.append(dict(id=i,size=s,off=o,type=t)); p+=24
    return out

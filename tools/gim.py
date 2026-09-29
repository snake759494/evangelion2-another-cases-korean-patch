"""GIM (MIG.00.1PSP) font atlas in dig 0002 member 2: 8bpp swizzled pages + palette."""
import struct,sys,numpy as np
sys.path.insert(0,'tools')
from swz import unswizzle,swizzle
def pages(g):
    """return list of dict(pal_off, img_off, w, h, data_off)"""
    out=[]; p=0x20
    end=struct.unpack_from('<I',g,0x14)[0]+0x10
    while p<end:
        bid,_,size,_,dat=struct.unpack_from('<HHIII',g,p)
        if bid!=3: break
        q=p+dat; ent={}
        while q<p+size:
            b2,_,s2,_,d2=struct.unpack_from('<HHIII',g,q)
            h=q+d2
            w,hh=struct.unpack_from('<HH',g,h+8)
            doff=h+struct.unpack_from('<I',g,h+0x1c)[0]
            ent[b2]=dict(w=w,h=hh,data=doff)
            q+=s2
        out.append(ent); p+=size
    return out
def page_pixels(g,ent):
    im=ent[4]; w,h=im['w'],im['h']
    raw=g[im['data']:im['data']+w*h]
    return np.frombuffer(unswizzle(raw,w,h),np.uint8).reshape(h,w)
def palette(g,ent):
    p=ent[5]; return np.frombuffer(g[p['data']:p['data']+1024],np.uint8).reshape(256,4)

"""Build the Korean font atlas (dig 0002 member 2 GIM) and width table (member 4).
Index layout: 0x00-0x5d ASCII (original glyphs kept), 0x5e.. assigned chars.
Chars that exist in the original atlas and are not Hangul keep the original glyph image."""
import sys,numpy as np;sys.path.insert(0,'tools')
from PIL import Image,ImageDraw,ImageFont
from gim import pages,page_pixels
from swz import swizzle
FONT='NanumSquareNeo-bRg.ttf'; SIZE=16
def alpha_to_idx(a):
    return np.clip(np.rint((255-a)/2.0),0,128).astype(np.uint8)
def render(ch,f):
    im=Image.new('L',(16,16)); dr=ImageDraw.Draw(im)
    dr.text((7.5,8),ch,font=f,fill=255,anchor='mm')
    a=np.asarray(im,np.float32)
    a[:,15]=0  # keep right column clear (advance 15)
    return a
def build(g,assign,orig_glyph_idx):
    """g: original GIM bytes; assign: list of chars for index 0x5e..; orig_glyph_idx: {char: original index} for non-Hangul reuse.
    returns new GIM bytes and width bytes list for indices."""
    g=bytearray(g); P=pages(g); f=ImageFont.truetype(FONT,SIZE)
    # page pixel arrays
    pix=[page_pixels(bytes(g),e).copy() for e in P]
    slots=sum(p.shape[0]//16*16 for p in pix)
    total=0x5e+len(assign)
    if total>slots: raise Exception('too many glyphs %d > %d'%(total,slots))
    def cell(i):
        pg=0
        while i>=pix[pg].shape[0]//16*16: i-=pix[pg].shape[0]//16*16; pg+=1
        r,c=divmod(i,16); return pg,r*16,c*16
    orig=[p.copy() for p in pix]
    widths={}
    for k,ch in enumerate(assign):
        i=0x5e+k; pg,y,x=cell(i)
        if ch in orig_glyph_idx:
            j=orig_glyph_idx[ch]; opg,oy,ox=cell(j)
            pix[pg][y:y+16,x:x+16]=orig[opg][oy:oy+16,ox:ox+16]
        else:
            pix[pg][y:y+16,x:x+16]=alpha_to_idx(render(ch,f))
        widths[i]=15
    # clear unused slots
    for i in range(total,slots):
        pg,y,x=cell(i); pix[pg][y:y+16,x:x+16]=128
    for e,p in zip(P,pix):
        im=e[4]; h,w=p.shape
        g[im['data']:im['data']+w*h]=swizzle(p.tobytes(),w,h)
    return bytes(g),widths

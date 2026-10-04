#!/bin/bash
# usage: bisect_run.sh RANGE NAME   (EBOOT strings in hex range only, no images) -> scratchpad/NAME_sheet.png
P=/c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계; cd $P
ESTR_RANGE=$1 IMG_ONLY=__none__ PYTHONIOENCODING=utf-8 python tools/build.py work/bis.iso 2>&1 | grep -E "verified|FAIL|INCONS"
timeout 1200 bash tools/go_s2room.sh "$P/work/bis.iso" $2 2>/dev/null; bash tools/emu_release.sh
S="C:/Users/Jay/AppData/Local/Temp/claude/C--Users-Jay-Downloads-psp---------2-------/c66b1edd-d5d4-496f-81a3-681081620472/scratchpad/"
python -c "
from PIL import Image
sh=Image.new('RGB',(480*4,272))
for k,i in enumerate([2,4,6,7]):
    try: im=Image.open('$S$2_%d.png'%i).resize((480,272)); sh.paste(im,(k*480,0))
    except Exception: pass
sh.save('$S$2_sheet.png')"

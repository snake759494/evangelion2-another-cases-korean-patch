#!/bin/bash
# boot $1, scenario 2, advance to Shinji's room; screenshot prefix $2
P=/c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계
L=/d/psp/ppsspp_win/LOCK.txt
while [ -f $L ] && [ "$(cat $L)" != "에반게리온2" ]; do sleep 5; done; echo 에반게리온2 > $L
bash /c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계/tools/emu_kill.sh; sleep 2
(cd /d/psp/ppsspp_win && ./PPSSPPWindows64.exe "$(cygpath -w "$1")" &)
sleep 28
cd $P
python tools/shot.py ${2}_a start w7 circle w9
python tools/shot.py ${2}_b down w2 circle w8
for i in 1 2 3 4 5 6 7 8; do python tools/shot.py ${2}_$i circle w1 circle w1 start w1 circle w2; done

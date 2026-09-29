#!/bin/bash
# boot ISO ($1) and go to scenario select, screenshot name $2
P=/c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계
L=/d/psp/ppsspp_win/LOCK.txt
while [ -f $L ] && [ "$(cat $L)" != "에반게리온2" ]; do sleep 5; done; echo 에반게리온2 > $L
taskkill //IM PPSSPPWindows64.exe //F >/dev/null 2>&1; sleep 1
(cd /d/psp/ppsspp_win && ./PPSSPPWindows64.exe "$(cygpath -w "$1")" &)
sleep 28
cd $P; python tools/shot.py ${2}_a start w7 circle w9

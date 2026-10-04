#!/bin/bash
# usage: boottest.sh iso seconds   (acquires D:/psp/ppsspp_win/LOCK.txt; release with tools/emu_release.sh)
L=/d/psp/ppsspp_win/LOCK.txt
if [ "$(cat $L 2>/dev/null)" != "에반게리온2" ]; then
  while [ -f $L ]; do sleep 5; done
  echo "에반게리온2" > $L
fi
bash /c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계/tools/emu_kill.sh; sleep 1
cd /d/psp/ppsspp_win && (./PPSSPPWindows64.exe "$(cygpath -w "$1")" &)
sleep ${2:-30}
cd /c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계
python tools/shot.py boot

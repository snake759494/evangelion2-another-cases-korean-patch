#!/bin/bash
bash /c/Users/Jay/Downloads/psp/신세기에반게리온2-만들어진세계/tools/emu_kill.sh
L=/d/psp/ppsspp_win/LOCK.txt
[ "$(cat $L 2>/dev/null)" = "에반게리온2" ] && rm -f $L
true

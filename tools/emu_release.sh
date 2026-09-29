#!/bin/bash
taskkill //IM PPSSPPWindows64.exe //F >/dev/null 2>&1
L=/d/psp/ppsspp_win/LOCK.txt
[ "$(cat $L 2>/dev/null)" = "에반게리온2" ] && rm -f $L
true

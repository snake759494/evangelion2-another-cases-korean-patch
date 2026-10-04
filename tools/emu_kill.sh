#!/bin/bash
# kill only the PPSSPP started from D:\psp\ppsspp_win (other sessions run their own copies)
powershell -NoProfile -Command "Get-Process PPSSPPWindows64 -ErrorAction SilentlyContinue | Where-Object { \$_.Path -like 'D:\psp\ppsspp_win\*' } | Stop-Process -Force" >/dev/null 2>&1
true

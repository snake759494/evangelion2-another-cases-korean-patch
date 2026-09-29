import sys,time;sys.path.insert(0,__import__('os').path.dirname(__file__))
from ppsspp_rpc import Debugger
S='C:/Users/Jay/AppData/Local/Temp/claude/C--Users-Jay-Downloads-psp---------2-------/c66b1edd-d5d4-496f-81a3-681081620472/scratchpad/'
d=Debugger()
for a in sys.argv[2:]:
    if a.startswith('w'): time.sleep(float(a[1:]))
    else: d.call('input.buttons.press',button=a,duration=4); time.sleep(0.8)
d.frame(S+sys.argv[1]+'.png')

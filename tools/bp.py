import sys,time,json,base64;sys.path.insert(0,'tools')
from ppsspp_rpc import Debugger,readmem
BASE=0x08804000
def wait_bp(d,addr,presses=(),timeout=20):
    d.call('cpu.breakpoint.add',address=BASE+addr,enabled=True)
    for b in presses: d.call('input.buttons.press',button=b,duration=4); time.sleep(0.8)
    t=time.time()
    while time.time()-t<timeout:
        s=d.call('cpu.status')
        if s['stepping']: break
        time.sleep(0.3)
    else: d.call('cpu.breakpoint.remove',address=BASE+addr); return None
    regs={n:d.call('cpu.getReg',name=n)['uintValue'] for n in ('pc','a0','a1','a2','a3','ra','sp')}
    d.call('cpu.breakpoint.remove',address=BASE+addr)
    return regs

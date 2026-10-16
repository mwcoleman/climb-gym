import asyncio, time, statistics
from forma_due import FormaDue
rows=[]
async def main():
    d=FormaDue(); await d.connect()
    d.on_sample=lambda t,kg,raw,tag,drift: rows.append((t,raw,tag,drift))
    await d.stream(); await asyncio.sleep(1.0); rows.clear()
    print(">>> KEEP THE 20 kg ON. Hold still for 10 s...",flush=True)
    for i in range(10):
        await asyncio.sleep(1)
        w=[r for _,r,t,_ in rows if t==0]; dd=sorted({x for _,_,t,x in rows if t==0})
        print(f"   {i+1:2d}s loaded   b0={statistics.mean(w[-28:]):6.1f}  b2={[hex(x) for x in dd[-3:]]}",flush=True)
    mark=len(rows)
    print("\n>>> NOW REMOVE THE 20 kg — let it hang free. 12 s...",flush=True)
    for i in range(12):
        await asyncio.sleep(1)
        w=[r for _,r,t,_ in rows[mark:] if t==0]; dd=sorted({x for _,_,t,x in rows[mark:] if t==0})
        if w: print(f"   {i+1:2d}s unloaded b0={statistics.mean(w[-28:]):6.1f}  b2={[hex(x) for x in dd[-3:]]}",flush=True)
    await d.stop()
    A=[(t,r,dd) for t,r,tg,dd in rows if tg==0]
    L=[x for x in A if x[0]<A[mark][0] if mark<len(A)] if mark<len(A) else []
    print("\n=== summary (channel 0x00) ===")
    half=A[:len(L)] if L else A[:len(A)//2]
    load=[x for x in A if x[0] <= rows[mark][0]]
    free=[x for x in A if x[0] >  rows[mark][0]+3]
    for nm,g in (("LOADED 20kg",load),("UNLOADED",free)):
        if not g: continue
        print(f"  {nm:12s} b0 mean={statistics.mean([x[1] for x in g]):7.2f}  "
              f"b2 values={sorted({hex(x[2]) for x in g})}")
    await d.disconnect()
asyncio.run(main())

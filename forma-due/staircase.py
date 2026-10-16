import asyncio, csv, statistics
from forma_due import FormaDue
rows=[]
async def main():
    d=FormaDue(); await d.connect()
    d.on_sample=lambda t,kg,raw,tag,drift: rows.append((t,raw,tag,drift))
    await d.stream(); await asyncio.sleep(1.0); rows.clear()
    await asyncio.sleep(150)
    await d.stop(); await d.disconnect()
    csv.writer(open("staircase.csv","w",newline="")).writerows([("t","counts","tag","aux")]+rows)
    A=[(t,v) for t,v,tg,_ in rows if tg==0]; t0=A[0][0]
    secs=[]
    for s in range(150):
        w=[v for t,v in A if s<=t-t0<s+1]
        if w: secs.append((s,statistics.mean(w),statistics.pstdev(w)))
    # merge consecutive stable seconds into plateaus
    plats=[]; cur=[]
    for s,m,sd in secs:
        if sd<6 and (not cur or abs(m-cur[-1][1])<8): cur.append((s,m))
        else:
            if len(cur)>=4: plats.append(cur)
            cur=[(s,m)] if sd<6 else []
    if len(cur)>=4: plats.append(cur)
    print(f"{len(A)} samples; detected {len(plats)} stable plateaus (>=4 s):\n")
    print("   window        mean counts   n")
    res=[]
    for p in plats:
        s0,s1=p[0][0],p[-1][0]
        vals=[v for t,v in A if s0<=t-t0<s1+1]
        m=statistics.mean(vals)
        print(f"   {s0:3d}-{s1:3d}s      {m:8.2f}    {len(vals)}")
        res.append(m)
    print("\n  plateau means:", [round(x,1) for x in res])
asyncio.run(main())

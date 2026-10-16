import asyncio, statistics, csv
from forma_due import FormaDue
rows=[]
async def main():
    d=FormaDue(); await d.connect()
    d.on_sample=lambda t,kg,raw,tag,drift: rows.append((t,raw,tag,drift))
    await d.stream(); await asyncio.sleep(1.0); rows.clear()
    await asyncio.sleep(90)
    await d.stop(); await d.disconnect()
    with open("plateau.csv","w",newline="") as f:
        csv.writer(f).writerows([("t","b0","tag","b2")]+rows)
    A=[(t,r,dd) for t,r,tg,dd in rows if tg==0]
    # 1-second buckets
    print(f"captured {len(rows)} pkts over 90s (channel 0x00 shown)\n")
    print("  sec   b0 mean   b0 sd   b2")
    buckets=[]
    for s in range(90):
        w=[(r,dd) for t,r,dd in A if s<=t-A[0][0]<s+1]
        if not w: continue
        m=statistics.mean([x[0] for x in w]); sd=statistics.pstdev([x[0] for x in w])
        b2=sorted({x[1] for x in w})
        buckets.append((s,m,sd,b2))
    for s,m,sd,b2 in buckets:
        flag=""
        if buckets and abs(m-buckets[0][1])>10: flag="  <-- CHANGED"
        print(f"  {s:3d}   {m:7.2f}   {sd:5.2f}   {[hex(x) for x in b2]}{flag}")
    lvls=sorted({round(m/5)*5 for _,m,sd,_ in buckets if sd<3})
    print(f"\n  stable levels (rounded/5): {lvls}")
asyncio.run(main())

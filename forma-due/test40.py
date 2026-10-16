import asyncio, statistics, csv
from forma_due import FormaDue
rows=[]
async def main():
    d=FormaDue(); await d.connect()
    d.on_sample=lambda t,kg,raw,tag,drift: rows.append((t,raw,tag,drift))
    await d.stream(); await asyncio.sleep(1.0); rows.clear()
    await asyncio.sleep(90)
    await d.stop(); await d.disconnect()
    csv.writer(open("test40.csv","w",newline="")).writerows([("t","b0","tag","b2")]+rows)
    A=[(t,r,dd) for t,r,tg,dd in rows if tg==0]
    t0=A[0][0]
    # compress into stable plateaus
    out=[]
    for s in range(90):
        w=[(r,dd) for t,r,dd in A if s<=t-t0<s+1]
        if not w: continue
        m=statistics.mean([x[0] for x in w]); sd=statistics.pstdev([x[0] for x in w])
        out.append((s,m,sd,sorted({x[1] for x in w})))
    print("plateaus (consecutive seconds with similar mean merged):")
    cur=None
    for s,m,sd,b2 in out:
        if cur and abs(m-cur[1])<4 and sd<4:
            cur=(cur[0],(cur[1]*cur[3]+m)/(cur[3]+1),cur[2]|set(b2),cur[3]+1,s)
        else:
            if cur: print(f"  t={cur[0]:2d}-{cur[4]:2d}s  b0={cur[1]:7.2f}  b2={[hex(x) for x in sorted(cur[2])]}")
            cur=(s,m,set(b2),1,s)
    if cur: print(f"  t={cur[0]:2d}-{cur[4]:2d}s  b0={cur[1]:7.2f}  b2={[hex(x) for x in sorted(cur[2])]}")
    peak=max(r for _,r,_ in A)
    print(f"\n  PEAK b0 = {peak}   b2 values over run = {[hex(x) for x in sorted({d for _,_,d in A})]}")
    print(f"  all b0 values >240: {sorted({r for _,r,_ in A if r>240})}")
asyncio.run(main())

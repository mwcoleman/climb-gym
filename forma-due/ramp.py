import asyncio, csv
from forma_due import FormaDue
rows=[]
async def main():
    d=FormaDue(); await d.connect()
    d.on_sample=lambda t,kg,raw,tag,drift: rows.append((t,raw,tag,drift))
    await d.stream(); await asyncio.sleep(1.0); rows.clear()
    await asyncio.sleep(75)
    await d.stop(); await d.disconnect()
    csv.writer(open("ramp.csv","w",newline="")).writerows([("t","b0","tag","b2")]+rows)
    A=[(t,b,d) for t,b,tg,d in rows if tg==0]
    t0=A[0][0]
    print(f"{len(A)} ch-A samples over 75s")
    # gaps
    gaps=[(A[i-1][0]-t0,A[i][0]-t0) for i in range(1,len(A)) if A[i][0]-A[i-1][0]>0.5]
    print(f"dropout gaps >0.5s: {[(round(a,1),round(b,1)) for a,b in gaps] or 'none'}")
    print(f"max b0 = {max(b for _,b,_ in A)}   count of b0==255: {sum(1 for _,b,_ in A if b==255)}")
    print(f"b0 values >=248 seen: {sorted({b for _,b,_ in A if b>=248})}")
    print(f"b2 values: {[hex(x) for x in sorted({d for _,_,d in A})]}")
    print("\nb2 transitions (b0 before -> after):")
    prev=None
    for t,b,dd in A:
        if prev and dd!=prev[2]:
            print(f"  t={t-t0:6.2f}  b2 0x{prev[2]:02x}->0x{dd:02x}   b0 {prev[1]:3d}->{b:3d}")
        prev=(t,b,dd)
    print("\nWRAP check (b0 drop >120 between consecutive samples):")
    prev=None; found=False
    for t,b,dd in A:
        if prev and prev[1]-b>120:
            print(f"  t={t-t0:6.2f}  b0 {prev[1]:3d}->{b:3d}  b2 0x{prev[2]:02x}->0x{dd:02x}  <-- WRAP"); found=True
        prev=(t,b,dd)
    if not found: print("  none")
    print("\nhighest-load window (20 samples around peak):")
    i=max(range(len(A)), key=lambda i:A[i][1])
    for t,b,dd in A[max(0,i-10):i+10]:
        print(f"  {t-t0:6.2f}  b0={b:3d}  b2=0x{dd:02x}")
asyncio.run(main())

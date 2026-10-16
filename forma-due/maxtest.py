import asyncio, time
from bleak import BleakClient, BleakScanner
ADDR="30181D09-52E7-1266-390F-CA75BF7CDA3B"
CTRL="c8770637-1739-4677-b3aa-ca4bf61608a7"; DATA="00767e89-b02b-487f-b636-9ccbd1e6acac"
rows=[]
async def main():
    d=await BleakScanner.find_device_by_address(ADDR,timeout=20.0)
    async with BleakClient(d,timeout=30.0) as c:
        t0=time.time()
        await c.start_notify(DATA, lambda _,x: rows.append((time.time()-t0, bytes(x))))
        await c.write_gatt_char(CTRL,b"\x01",response=True)
        print("25s: PULL AS HARD AS YOU CAN, ramping to absolute max, hold 3s, release.\n",flush=True)
        while time.time()-t0<25:
            await asyncio.sleep(2.5)
            A=[b for _,b in rows if b[1]==0]
            if A: print(f"  t={time.time()-t0:4.1f}s  b0 max so far={max(x[0] for x in A):3d}  b2 seen={sorted({x[2] for x in A})}",flush=True)
        await c.write_gatt_char(CTRL,b"\x00",response=True)
    A=[(t,b) for t,b in rows if b[1]==0]
    mx=max(b[0] for _,b in A)
    print(f"\nPEAK b0 = {mx}")
    # look for wrap: b0 drops >200 between consecutive samples while b2 increments
    print("suspected wraps:")
    prev=None
    for t,b in A:
        if prev and prev[0]>200 and b[0]<60 and b[2]!=prev[2]:
            print(f"  t={t:.3f} {prev.hex()} -> {b.hex()}  <-- WRAP")
        prev=b
    print("samples at peak region:")
    pk=[ (t,b) for t,b in A if b[0]>=mx-12 ]
    for t,b in pk[:25]: print(f"  {t:6.3f} {b.hex()}")
asyncio.run(main())

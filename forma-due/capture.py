import asyncio, time, struct, sys, csv
from bleak import BleakClient, BleakScanner
ADDR="30181D09-52E7-1266-390F-CA75BF7CDA3B"
DATA="00767e89-b02b-487f-b636-9ccbd1e6acac"; CTRL="c8770637-1739-4677-b3aa-ca4bf61608a7"
DUR=float(sys.argv[1]) if len(sys.argv)>1 else 40.0
rows=[]; t0=0
async def main():
    global t0
    d=await BleakScanner.find_device_by_address(ADDR,timeout=20.0)
    async with BleakClient(d,timeout=30.0) as c:
        def cb(_,data):
            rows.append((time.time()-t0, data.hex()))
        await c.start_notify(DATA, cb)
        t0=time.time()
        await c.write_gatt_char(CTRL,b"\x01",response=True)
        print(f"STREAMING for {DUR:.0f}s -- PULL ON THE GAUGE, hard, a few times!",flush=True)
        last=0
        while time.time()-t0 < DUR:
            await asyncio.sleep(2)
            n=len(rows)
            recent=[r[1] for r in rows[last:]]
            uniq=sorted(set(recent))
            print(f"  t={time.time()-t0:5.1f}s pkts={n:<6} distinct_in_window={len(uniq):<4} sample={uniq[:4]}",flush=True)
            last=n
        await c.write_gatt_char(CTRL,b"\x00",response=True)
    with open("capture.csv","w",newline="") as f:
        w=csv.writer(f); w.writerow(["t","hex"]); w.writerows(rows)
    print(f"\nwrote capture.csv  ({len(rows)} packets)",flush=True)
asyncio.run(main())

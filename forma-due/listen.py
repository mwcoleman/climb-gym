import asyncio, time, struct, sys
from bleak import BleakClient, BleakScanner

ADDR = "30181D09-52E7-1266-390F-CA75BF7CDA3B"
NOTIFY = ["00002a19-0000-1000-8000-00805f9b34fb",
 "ab27449b-448e-44fd-b587-624890f82b16","c8770637-1739-4677-b3aa-ca4bf61608a7",
 "00767e89-b02b-487f-b636-9ccbd1e6acac","12b92911-f3d2-4f6f-b23f-406215986291",
 "48c99f3c-833a-4148-8cff-6938fc08a8f3","66e178e3-58d6-4253-a75b-30a754b1f431",
 "b6101851-e548-40bc-8ee0-ba6f4a8ae545","c64f970a-61e6-41c6-8028-4810c5dba638"]
t0 = time.time(); counts = {}

def mk(u):
    short = u[:8]
    def cb(_, data):
        counts[short] = counts.get(short,0)+1
        if counts[short] <= 6 or counts[short] % 50 == 0:
            fl = ""
            if len(data) >= 4 and len(data) % 4 == 0:
                fl = " floats=" + str([round(f,3) for f in struct.unpack("<%df"%(len(data)//4), data)])
            print(f"[{time.time()-t0:6.2f}] {short} #{counts[short]:<5} {data.hex()}{fl}", flush=True)
    return cb

async def main():
    d = await BleakScanner.find_device_by_address(ADDR, timeout=20.0)
    async with BleakClient(d, timeout=30.0) as c:
        print("connected; subscribing to all notify chars\n", flush=True)
        for u in NOTIFY:
            try: await c.start_notify(u, mk(u))
            except Exception as e: print(f"  sub fail {u[:8]}: {e}")
        print("--- PASSIVE LISTEN 20s (pull on the gauge now!) ---", flush=True)
        await asyncio.sleep(20)
        print("\n--- totals:", counts, flush=True)

asyncio.run(main())

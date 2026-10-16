import asyncio, time, struct, statistics, collections
from bleak import BleakClient, BleakScanner
ADDR="30181D09-52E7-1266-390F-CA75BF7CDA3B"
CTRL="c8770637-1739-4677-b3aa-ca4bf61608a7"; DATA="00767e89-b02b-487f-b636-9ccbd1e6acac"
NOTIFY=["00002a19-0000-1000-8000-00805f9b34fb",
 "ab27449b-448e-44fd-b587-624890f82b16","c8770637-1739-4677-b3aa-ca4bf61608a7",
 "00767e89-b02b-487f-b636-9ccbd1e6acac","12b92911-f3d2-4f6f-b23f-406215986291",
 "48c99f3c-833a-4148-8cff-6938fc08a8f3","66e178e3-58d6-4253-a75b-30a754b1f431",
 "b6101851-e548-40bc-8ee0-ba6f4a8ae545","c64f970a-61e6-41c6-8028-4810c5dba638"]
READ=["ab27449b-448e-44fd-b587-624890f82b16","12b92911-f3d2-4f6f-b23f-406215986291",
 "48c99f3c-833a-4148-8cff-6938fc08a8f3","66e178e3-58d6-4253-a75b-30a754b1f431",
 "b6101851-e548-40bc-8ee0-ba6f4a8ae545","c64f970a-61e6-41c6-8028-4810c5dba638",
 "00767e89-b02b-487f-b636-9ccbd1e6acac"]
hits=collections.defaultdict(list); t0=0
def mk(u):
    s=u[:8]
    def cb(_,data): hits[s].append((time.time()-t0, bytes(data)))
    return cb
async def main():
    global t0
    d=await BleakScanner.find_device_by_address(ADDR,timeout=20.0)
    async with BleakClient(d,timeout=30.0) as c:
        t0=time.time()
        for u in NOTIFY:
            try: await c.start_notify(u,mk(u))
            except Exception as e: print("sub fail",u[:8],e)
        await c.write_gatt_char(CTRL,b"\x01",response=True)
        print("streaming with 30 kg on; 20 s capture + polling all read chars\n",flush=True)
        prev={}
        for i in range(20):
            await asyncio.sleep(1.0)
            for u in READ:
                try: v=bytes(await c.read_gatt_char(u))
                except Exception: continue
                if prev.get(u)!=v:
                    print(f"  [{i+1:2d}s] READ {u[:8]} = {v.hex()}",flush=True); prev[u]=v
        await c.write_gatt_char(CTRL,b"\x00",response=True)
    print("\n=== notification summary ===")
    for s,v in sorted(hits.items()):
        uniq=collections.Counter(x[1].hex() for x in v)
        print(f"  {s}: {len(v)} pkts, {len(uniq)} distinct")
        for h,n in uniq.most_common(6): print(f"      {h}  x{n}")
    D=[x[1] for x in hits.get("00767e89",[])]
    if D:
        for tag in sorted({p[1] for p in D}):
            g=[p for p in D if p[1]==tag]
            b0=[p[0] for p in g]
            print(f"\n  tag 0x{tag:02x}: n={len(g)}  b0 mean={statistics.mean(b0):7.2f} "
                  f"min={min(b0)} max={max(b0)}  b2={sorted({hex(p[2]) for p in g})}")
        print(f"\n  >>> b0 == 255 count: {sum(1 for p in D if p[0]==255)}")
        print(f"  >>> predicted if 16-bit (30kg=261cnt): b0~5, b2=0x4e")
        print(f"  >>> predicted if 8-bit clamp:          b0=255")
asyncio.run(main())

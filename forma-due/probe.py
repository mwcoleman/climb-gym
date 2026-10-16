import asyncio, time, struct, sys
from bleak import BleakClient, BleakScanner

ADDR = "30181D09-52E7-1266-390F-CA75BF7CDA3B"
NOTIFY = ["ab27449b-448e-44fd-b587-624890f82b16","c8770637-1739-4677-b3aa-ca4bf61608a7",
 "00767e89-b02b-487f-b636-9ccbd1e6acac","12b92911-f3d2-4f6f-b23f-406215986291",
 "48c99f3c-833a-4148-8cff-6938fc08a8f3","66e178e3-58d6-4253-a75b-30a754b1f431",
 "b6101851-e548-40bc-8ee0-ba6f4a8ae545","c64f970a-61e6-41c6-8028-4810c5dba638"]
t0=time.time(); counts={}
def mk(u):
    s=u[:8]
    def cb(_,data):
        counts[s]=counts.get(s,0)+1
        if counts[s]<=8:
            fl=""
            if len(data)>=4 and len(data)%4==0:
                fl=" f="+str([round(f,3) for f in struct.unpack("<%df"%(len(data)//4),data)])
            print(f"[{time.time()-t0:6.2f}] {s} #{counts[s]:<4} {data.hex()}{fl}",flush=True)
    return cb

async def main():
    d=await BleakScanner.find_device_by_address(ADDR,timeout=20.0)
    async with BleakClient(d,timeout=30.0) as c:
        for u in NOTIFY:
            try: await c.start_notify(u,mk(u))
            except Exception: pass
        for val in (b"\x01", b"\x02"):
            counts.clear()
            print(f"\n=== write {val.hex()} -> c8770637 ===",flush=True)
            try: await c.write_gatt_char("c8770637-1739-4677-b3aa-ca4bf61608a7", val, response=True)
            except Exception as e: print("  write err:",e,flush=True)
            await asyncio.sleep(6)
            print("  totals:",counts,flush=True)
        print("\n=== write 00 (stop) ===",flush=True)
        try: await c.write_gatt_char("c8770637-1739-4677-b3aa-ca4bf61608a7", b"\x00", response=True)
        except Exception as e: print(e)

asyncio.run(main())

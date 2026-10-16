import asyncio, time, struct
from bleak import BleakClient, BleakScanner
ADDR="30181D09-52E7-1266-390F-CA75BF7CDA3B"
CTRL="c8770637-1739-4677-b3aa-ca4bf61608a7"; DATA="00767e89-b02b-487f-b636-9ccbd1e6acac"
READ=["ab27449b-448e-44fd-b587-624890f82b16","12b92911-f3d2-4f6f-b23f-406215986291",
 "48c99f3c-833a-4148-8cff-6938fc08a8f3","66e178e3-58d6-4253-a75b-30a754b1f431",
 "b6101851-e548-40bc-8ee0-ba6f4a8ae545","c64f970a-61e6-41c6-8028-4810c5dba638"]
last={}; cur_b0=[0]
async def main():
    d=await BleakScanner.find_device_by_address(ADDR,timeout=20.0)
    async with BleakClient(d,timeout=30.0) as c:
        def cb(_,data): cur_b0[0]=data[0]
        await c.start_notify(DATA,cb)
        await c.write_gatt_char(CTRL,b"\x01",response=True)
        print("streaming; polling read-chars 30s -- PULL HARD a few times\n",flush=True)
        t0=time.time()
        while time.time()-t0<30:
            for u in READ:
                try: v=bytes(await c.read_gatt_char(u))
                except Exception: continue
                if last.get(u)!=v:
                    fl=""
                    if len(v)>=4 and len(v)%4==0:
                        fl="  f="+str([round(f,4) for f in struct.unpack("<%df"%(len(v)//4),v)])
                    print(f"[{time.time()-t0:5.1f}] b0={cur_b0[0]:3d}  {u[:8]} {v.hex()}{fl}",flush=True)
                    last[u]=v
            await asyncio.sleep(0.15)
        await c.write_gatt_char(CTRL,b"\x00",response=True)
asyncio.run(main())

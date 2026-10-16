import asyncio, time, collections
from bleak import BleakClient, BleakScanner
ADDR="30181D09-52E7-1266-390F-CA75BF7CDA3B"
CTRL="c8770637-1739-4677-b3aa-ca4bf61608a7"; DATA="00767e89-b02b-487f-b636-9ccbd1e6acac"
RATE="ab27449b-448e-44fd-b587-624890f82b16"
buf=[]
async def main():
    d=await BleakScanner.find_device_by_address(ADDR,timeout=20.0)
    async with BleakClient(d,timeout=30.0) as c:
        await c.start_notify(DATA, lambda _,x: buf.append(bytes(x)))
        for m in range(1,9):
            buf.clear()
            try: await c.write_gatt_char(CTRL,bytes([m]),response=True)
            except Exception as e: print(f"mode {m}: write err {e}"); continue
            await asyncio.sleep(3)
            lens=collections.Counter(len(x) for x in buf)
            tags=collections.Counter(x[1] for x in buf if len(x)>1)
            print(f"mode {m:2d}: {len(buf):4d} pkts/3s ({len(buf)/3:5.1f}Hz) lens={dict(lens)} tags={dict(tags)} ex={buf[0].hex() if buf else '-'}",flush=True)
            await c.write_gatt_char(CTRL,b"\x00",response=True); await asyncio.sleep(0.3)
        # try raising sample rate
        print("\n-- rate char ab27449b --",flush=True)
        for r in (60,100):
            try:
                await c.write_gatt_char(RATE,bytes([r]),response=True)
                rb=bytes(await c.read_gatt_char(RATE)); buf.clear()
                await c.write_gatt_char(CTRL,b"\x01",response=True); await asyncio.sleep(3)
                print(f"  set {r} -> readback {rb.hex()}  {len(buf)/3:.1f} pkts/s",flush=True)
                await c.write_gatt_char(CTRL,b"\x00",response=True); await asyncio.sleep(0.3)
            except Exception as e: print(f"  {r}: {e}",flush=True)
        await c.write_gatt_char(RATE,bytes([30]),response=True)
        print("  restored rate ->", bytes(await c.read_gatt_char(RATE)).hex(),flush=True)
asyncio.run(main())

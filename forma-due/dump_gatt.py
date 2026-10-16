import asyncio, sys
from bleak import BleakClient, BleakScanner

ADDR = "30181D09-52E7-1266-390F-CA75BF7CDA3B"

async def main():
    d = await BleakScanner.find_device_by_address(ADDR, timeout=20.0)
    if not d:
        print("not found"); return
    async with BleakClient(d, timeout=30.0) as c:
        print(f"connected: {c.address}\n")
        for s in c.services:
            print(f"SERVICE {s.uuid}  ({s.description})")
            for ch in s.characteristics:
                print(f"  CHAR {ch.uuid}  handle={ch.handle} props={','.join(ch.properties)}  ({ch.description})")
                if "read" in ch.properties:
                    try:
                        v = await c.read_gatt_char(ch)
                        try: txt = v.decode("utf-8")
                        except Exception: txt = ""
                        print(f"       value: {v.hex()}  len={len(v)}" + (f"  utf8={txt!r}" if txt.isprintable() and txt else ""))
                    except Exception as e:
                        print(f"       read err: {e}")
                for de in ch.descriptors:
                    print(f"       DESC {de.uuid} handle={de.handle}")
                    try:
                        dv = await c.read_gatt_descriptor(de.handle)
                        print(f"            {dv.hex()} {dv!r}")
                    except Exception as e:
                        print(f"            err: {e}")
            print()

asyncio.run(main())

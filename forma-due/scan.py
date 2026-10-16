import asyncio
from bleak import BleakScanner

async def main():
    print("Scanning 10s...\n")
    devs = await BleakScanner.discover(timeout=10.0, return_adv=True)
    for addr, (d, adv) in sorted(devs.items(), key=lambda kv: -(kv[1][1].rssi or -999)):
        name = adv.local_name or d.name or "(no name)"
        print(f"{name!r:40} {addr}  rssi={adv.rssi}")
        if adv.service_uuids:
            print(f"    services: {adv.service_uuids}")
        if adv.manufacturer_data:
            for k, v in adv.manufacturer_data.items():
                print(f"    mfr 0x{k:04x}: {v.hex()}")
        if adv.service_data:
            for k, v in adv.service_data.items():
                print(f"    svcdata {k}: {v.hex()}")

asyncio.run(main())

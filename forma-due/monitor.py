#!/usr/bin/env python3
"""Live force readout from the Forma Due. Usage: python monitor.py [seconds]"""
import asyncio, sys, time
from forma_due import FormaDue

async def main():
    dur = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0
    d = FormaDue()
    await d.connect()
    info = await d.info()
    print(f"Forma Due  fw={info['firmware']}  sn={info['serial']}  batt={info['battery_pct']}%")
    cal = d.cal.get("counts_per_kg", 1.0)
    unit = "kg" if cal != 1.0 else "counts"
    if cal == 1.0:
        print("(uncalibrated -- showing raw counts; run calibrate.py <known_kg>)")
    peak = [0.0]; last = [0.0]
    def cb(t, kg, raw, tag, drift):
        v = kg if cal != 1.0 else raw
        last[0] = v; peak[0] = max(peak[0], v)
    d.on_sample = cb
    await d.stream()
    await asyncio.sleep(1.0); await d.tare(1.5)
    print("tared. pull!\n")
    t0 = time.time()
    while time.time() - t0 < dur:
        v, p = last[0], peak[0]
        bar = "#" * int(max(0, min(50, v / max(p, 1e-9) * 50 if p else 0)))
        print(f"\r  {v:8.2f} {unit}   peak {p:8.2f}   |{bar:<50}|", end="", flush=True)
        await asyncio.sleep(0.05)
    print()
    await d.disconnect()

asyncio.run(main())

#!/usr/bin/env python3
"""Calibrate the Forma Due: map raw counts -> kg using a known weight.

Usage:  python calibrate.py 20.0        # hang a 20 kg known mass
The device's byte-0 reading is 8-bit and saturates near 247, so pick a weight
comfortably inside the range (roughly 30-70% of what you can pull).
"""
import asyncio, json, statistics, sys
from forma_due import FormaDue, CAL_FILE


async def main():
    if len(sys.argv) < 2:
        print(__doc__); return
    known = float(sys.argv[1])
    d = FormaDue()
    await d.connect()
    print("connected:", await d.info())

    samples = []
    d.on_sample = lambda t, kg, raw, tag, drift: samples.append((t, raw, tag))
    await d.stream()

    print("\n1/2  UNLOADED -- leave the gauge hanging free. Taring in 3s...")
    await asyncio.sleep(3)
    zero = await d.tare(2.0)
    print(f"     zero per channel: { {hex(k): round(v,2) for k,v in zero.items()} }")

    print(f"\n2/2  LOAD IT with exactly {known} kg and hold steady. Measuring in 5s...")
    await asyncio.sleep(5)
    samples.clear()
    await asyncio.sleep(4)
    await d.stop()

    per = {}
    for _, raw, tag in samples:
        per.setdefault(tag, []).append(raw - zero.get(tag, 0))
    if not per:
        print("no samples captured"); await d.disconnect(); return

    print("\n  channel   mean counts   stdev")
    allc = []
    for tag, vals in sorted(per.items()):
        m = statistics.mean(vals); s = statistics.pstdev(vals)
        print(f"  0x{tag:02x}      {m:9.2f}   {s:6.2f}")
        allc.extend(vals)
    mean_counts = statistics.mean(allc)
    if mean_counts < 5:
        print("\n!! almost no load detected -- was the weight applied?")
        await d.disconnect(); return

    cpk = mean_counts / known
    cal = {"counts_per_kg": round(cpk, 4),
           "known_weight_kg": known,
           "mean_counts": round(mean_counts, 2),
           "saturates_at_counts": 247,
           "max_kg_estimate": round(247 / cpk, 1),
           "note": "byte0 is 8-bit; resolution = 1/counts_per_kg kg"}
    with open(CAL_FILE, "w") as f:
        json.dump(cal, f, indent=2)
    print(f"\n  {mean_counts:.2f} counts = {known} kg")
    print(f"  -> {cpk:.4f} counts/kg   (resolution {1/cpk:.3f} kg, full scale ~{247/cpk:.1f} kg)")
    print(f"  saved {CAL_FILE}")
    await d.disconnect()

asyncio.run(main())

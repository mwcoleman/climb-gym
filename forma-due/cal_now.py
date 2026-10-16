#!/usr/bin/env python3
"""Calibrate against a weight that is ALREADY hanging. Usage: cal_now.py 20.0"""
import asyncio, json, statistics, sys
from forma_due import FormaDue, CAL_FILE

async def main():
    known = float(sys.argv[1])
    d = FormaDue()
    await d.connect()
    print("connected:", (await d.info())["firmware"], "- NOT taring (load is on)")
    s = []
    d.on_sample = lambda t, kg, raw, tag, drift: s.append((t, raw, tag, drift))
    await d.stream()
    await asyncio.sleep(1.0); s.clear()          # discard startup
    print(f"measuring 8 s with {known} kg hanging...", flush=True)
    for i in range(8):
        await asyncio.sleep(1.0)
        w = [r for _, r, _, _ in s]
        print(f"  t={i+1}s  n={len(w):4d}  mean b0={statistics.mean(w):7.2f}  "
              f"min={min(w)} max={max(w)}", flush=True)
    await d.stop()

    per = {}
    for _, raw, tag, _ in s: per.setdefault(tag, []).append(raw)
    print("\n  channel   n     mean      stdev")
    for tag, v in sorted(per.items()):
        print(f"  0x{tag:02x}    {len(v):4d}  {statistics.mean(v):7.2f}   {statistics.pstdev(v):6.2f}")
    allv = [r for _, r, _, _ in s]
    mean = statistics.mean(allv)
    drift = sorted({dd for _, _, _, dd in s})
    print(f"\n  overall mean b0 = {mean:.2f} counts for {known} kg")
    print(f"  drift byte values seen: {[hex(x) for x in drift]}")
    if mean < 5:
        print("\n  !! near-zero reading - is the weight actually on the gauge?")
        await d.disconnect(); return
    if mean > 240:
        print("\n  !! reading is at/near the 247 saturation ceiling - calibration unreliable.")
    cpk = mean / known
    cal = {"counts_per_kg": round(cpk, 4), "known_weight_kg": known,
           "mean_counts": round(mean, 2), "zero_offset_counts": 0,
           "saturates_at_counts": 247, "max_kg_estimate": round(247 / cpk, 1),
           "resolution_kg": round(1 / cpk, 4),
           "method": "device self-tares (b0==0 at rest); measured with load already applied"}
    json.dump(cal, open(CAL_FILE, "w"), indent=2)
    print(f"\n  -> {cpk:.4f} counts/kg")
    print(f"  -> resolution {1/cpk:.3f} kg,  full scale ~{247/cpk:.1f} kg")
    print(f"  saved {CAL_FILE}")
    await d.disconnect()

asyncio.run(main())

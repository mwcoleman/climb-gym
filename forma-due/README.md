# Forma Due → Tindeq Progressor bridge

Makes a **Forma Due** climbing force gauge usable by any app that speaks the
**Tindeq Progressor** BLE API. See `PROTOCOL.md` for the reverse-engineered protocol.

## Setup
```bash
python3 -m venv .bleenv && .bleenv/bin/pip install bleak bless
```
(Already created at `../.bleenv`.) Grant your terminal Bluetooth permission in
System Settings → Privacy & Security → Bluetooth.

## 1. Check it reads
```bash
../.bleenv/bin/python monitor.py 30
```
Live readout + peak. Uncalibrated it shows raw counts.

## 2. Calibrate  ← required for real kg
```bash
../.bleenv/bin/python cal_now.py 20.0      # with the weight ALREADY hanging
```
Already done — `calibration.json` holds a 4-point staircase (0/10/20/30 kg).
Use `staircase.py` to redo it: start loaded, then unload in steps, pausing ~20 s each;
plateaus are auto-detected so timing does not matter.
Use `calibrate.py` instead if you want the guided unloaded→loaded version, but note its
prompts print to the terminal, which you may not see if run in the background.

## 3. Run the bridge
```bash
../.bleenv/bin/python tindeq_bridge.py
```
Connects to the Forma Due and simultaneously advertises this Mac as
`Progressor_1234` implementing the Tindeq GATT service. Point your Tindeq-compatible
app at it.

Supported Tindeq commands: tare (100), start/stop weight measurement (101/102),
get app version (107), get battery (111), get/clear error (108/109).
RFD opcodes (103/104) are accepted but not implemented — most apps compute rate of
force development from the weight stream anyway.

**Opcode 112 and DFU errors are expected.** The current Tindeq Android app sends an
undocumented opcode 112 (the published API stops at 111) and logs DFU errors when it goes
unanswered. The bridge intentionally stays silent: it then connects and streams normally.
Do not "fix" this by inventing a reply — it looks like a firmware-version probe, and a
plausible-looking answer could make the app attempt a Progressor firmware push.

## Files
| File | Purpose |
|---|---|
| `forma_due.py` | Driver library — connect, tare, stream, decode |
| `monitor.py` | Live force readout |
| `calibrate.py` | Known-weight calibration → `calibration.json` |
| `tindeq_bridge.py` | Tindeq Progressor peripheral emulation |
| `PROTOCOL.md` | Protocol documentation |
| `PORTING.md` | Moving the bridge to an ESP32 or Android |
| `scan.py`, `dump_gatt.py`, `capture.py`, `modes.py` | Reverse-engineering tools used to work it out |
| `staircase.py` | Multi-point unload calibration (auto-detects plateaus) |
| `maxtest.py`, `probe.py`, `ramp.py`, `test40.py` | Early RE scripts — these contain the **old buggy `b1 == 0x00` channel filter** and will under-report any load above 255 counts. Kept only for reference; do not reuse their decode logic. |

## Caveats
- **Full range, ~0.11 kg resolution.** The measurement is 14-bit
  (`value = ((byte1 & 0x3F) << 8) | byte0`), so there is no practical ceiling — peaks of
  625 counts (~65 kg) have been recorded. Calibrated 0/10/20/30 kg by staircase.
- **Above 30 kg is extrapolated.** The calibration only spans 0-30 kg; higher readings
  use the 20-30 kg slope. Cross-checks land within ~1 kg of known bodyweight, but hang a
  heavier known load and re-run the staircase if you need max-hang accuracy.
- **Slightly progressive response.** Segment slopes were 8.60 / 9.49 / 9.83 counts/kg, so
  the driver interpolates piecewise rather than using a single scale factor. This is more
  likely plate-weight tolerance than real sensor non-linearity.
- **~28.6 Hz per channel** (57 Hz if you merge both), vs Tindeq's higher rate.
- **macOS advertises its own device name** alongside `Progressor_1234` in some stacks.
  Apps that filter strictly on a `Progressor` name prefix may need the name adjusting
  (`ADV_NAME` in `tindeq_bridge.py`).
- A Mac cannot connect to its own advertised peripheral — test from a phone/tablet.

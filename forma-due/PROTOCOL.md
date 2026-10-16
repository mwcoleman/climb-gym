# Forma Due — BLE protocol (reverse-engineered 2026-10-10)

Device: `Forma#Due` · Manufacturer `Forma Training Pty Ltd Australia` · Firmware `8.0.0`

## Advertisement
Local name `Forma#Due`; advertises `0x180F` (Battery) and the custom service
`72d06610-1ea5-4ec7-8691-959b38283571`.

## GATT map

### Standard services
| Char | UUID | Props | Value |
|---|---|---|---|
| Battery Level | `2a19` | read, notify | `0x64` (100 %) |
| Device Name | `2a00` | read | 4-byte id |
| Firmware Rev | `2a26` | read | `8.0.0` (64-byte null-padded) |
| Manufacturer | `2a29` | read | `Forma Training Pty Ltd Australia` |
| Serial | `2a25` | read | `CC4533DB5110` |

### Main service `72d06610-1ea5-4ec7-8691-959b38283571`
| UUID | Props | Role |
|---|---|---|
| `058f4d90-36f5-484f-bf1b-9bd857605ea3` | write | **unknown — not probed** |
| `ab27449b-448e-44fd-b587-624890f82b16` | r/w/notify | `0x1e` = 30. Sample rate (Hz/channel). Writes are ignored. |
| `c8770637-1739-4677-b3aa-ca4bf61608a7` | r/w/notify | **Stream control.** `01` = start, `00` = stop. Only `01` starts; `02`–`08` do nothing. |
| `00767e89-b02b-487f-b636-9ccbd1e6acac` | read, notify | **Data stream** — 3-byte packets |
| `1d8798da-5748-4b87-ae2c-02743c2935f1` | write | **unknown — not probed** |
| `12b92911-f3d2-4f6f-b23f-406215986291` | r/notify | 1 byte state flag (seen `01`, `02`) |
| `48c99f3c-833a-4148-8cff-6938fc08a8f3` | r/notify | 16 B `013f00000000a84154ac060092b29c46` — contains float `21.0`, u32 `437844`, float `20057.29` |
| `66e178e3-58d6-4253-a75b-30a754b1f431` | r/w/notify | 16 B — floats **`1800000.0`, `1500000.0`** (ADC calibration counts) + u16 `25, 250, 500, 1` |
| `b6101851-e548-40bc-8ee0-ba6f4a8ae545` | r/w/notify | 16 B — floats **`1.775`, `1.79`** + u16 `50, 1` |

All config characteristics above stayed **static under load** — they are calibration/config, not live data.

### Second service `4a9ad582-1c69-4e64-8dd2-79ec46b85022`
`5cb3f143…` (write), `b2f8953f…` (write), `c64f970a…` (read/notify, 10 B zeros).
Deliberately **not probed** — most likely firmware update / factory calibration. Writing here risks bricking.

## Streaming

```
write 0x01 -> c8770637        # start
notifications on 00767e89     # 3-byte packets, ~57 Hz total
write 0x00 -> c8770637        # stop
```

### Packet layout — 3 bytes

```
byte 0   value_lo    low 8 bits of the measurement
byte 1   flags       bits 0-5 = value bits 8-13   |   bit 6 (0x40) = channel tag
byte 2   aux         slow drift indicator -- NOT force
```

```python
value   = ((pkt[1] & 0x3F) << 8) | pkt[0]     # 14-bit, 0..16383
channel = pkt[1] & 0x40                        # 0x00 or 0x40
```

**This is the critical detail.** Byte 1 is *not* a pure channel tag. Only bit 6 identifies
the channel; bits 0-5 carry the high bits of the measurement. Treating byte 1 as a tag and
filtering on `== 0x00` silently discards every sample above 255 counts, which manufactures
a convincing but entirely false "8-bit value that saturates at ~254" plus phantom
multi-second stream dropouts whenever the load goes over range. Observed byte-1 values
so far: `0x00/0x40`, `0x01/0x41`, `0x02/0x42`.

The wrap, caught in a slow ramp, is unambiguous:

```
t=42.63  b0=254  b1=0x00   -> 254
t=42.64  b0=  4  b1=0x41   -> 260      smooth continuation, no discontinuity
t=42.67  b0=  7  b1=0x01   -> 263
t=42.72  b0= 25  b1=0x01   -> 281
```

**Two interleaved channels** ("Due" = two load cells), each ~28.6 Hz, 57 Hz combined.
Both carry the same measurement to within ~1 count (at a steady 20 kg both read 170.73),
so either channel alone works; averaging the pair halves the noise.

**byte 2 is not force and not a high byte.** It held at `0x4d` across a full 0 kg <-> 20 kg
load-removal transition, and over a 75 s ramp it flipped *both directions* at constant
value (`183->183`, `172->172`), which a carry bit cannot do. The two channels' byte-2
values stay complementary (`aux(0x00) + aux(0x40)` = `0xa6`/`0xa7`). It drifts slowly
upward across a session (`0x49 -> 0x5a`) regardless of load.

Observed peaks with the correct decoder: **573 counts** (bodyweight hang) and **625 counts**
(ramp) — no ceiling, no saturation, no dropouts.

### Calibration (this unit, serial CC4533DB5110)

4-point staircase, single thermal session, unloading 30 -> 20 -> 10 -> 0 kg:

| load | counts | segment slope |
|---|---|---|
| 0 kg | 0.00 | |
| 10 kg | 86.04 | 8.604 counts/kg |
| 20 kg | 180.92 | 9.488 counts/kg |
| 30 kg | 279.17 | 9.825 counts/kg |

Linear fit `counts = 9.324*kg - 3.33` leaves systematic ±3.9-count residuals; a quadratic
`0.0305*kg^2 + 8.408*kg - 0.27` fits to ±0.8. The driver uses piecewise-linear
interpolation through the measured points and extrapolates above 30 kg with the last
segment's slope. Resolution is ~0.107 kg/count.

Cross-check against data not used in the fit: the ramp peak of 625 counts reads 65.2 kg
and the bodyweight hang of 573 counts reads 59.9 kg, against a stated bodyweight of ~65 kg
with "some taken off".

### Unresolved
- Exact meaning of byte 2 and the `0xa6` complement.
- Exact full-scale range (byte 1 allows 14 bits = 16383 counts, far beyond the load cell).
- The two write-only characteristics `058f4d90…` and `1d8798da…` (likely tare / mode).

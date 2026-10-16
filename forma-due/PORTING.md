# Porting the bridge off the Mac

The Python bridge works but ties the gauge to a laptop. Two ways off it.

## Option A — ESP32 (recommended)

A standalone dongle between the gauge and any phone. Nothing to install, no app to keep
alive; the phone just sees `Progressor_1234`.

**Hardware:** ESP32-C3 (cheap, BLE 5, low power), ESP32-S3, or an original ESP32.
**Do NOT use an ESP32-S2 — it has no Bluetooth at all, only WiFi.**

**Stack:** NimBLE-Arduino (PlatformIO) — or `esp-nimble-cpp` if building against ESP-IDF
directly, since NimBLE-Arduino does not compile cleanly as an IDF component.

**The one real constraint:** the radio cannot scan, advertise and connect simultaneously.
Sequence it explicitly, do not do all three at once:

```
1. scan for a device whose name starts with "Forma#"
2. STOP scanning
3. connect as central; write 0x01 to c8770637; subscribe to 00767e89
4. only THEN start advertising the Progressor service
5. on central disconnect: stop advertising, go back to step 1
```

Set `CONFIG_BT_NIMBLE_MAX_CONNECTIONS >= 2` (one inbound, one outbound).

**What the firmware has to do** — all of it is already solved in `forma_due.py` and
`tindeq_bridge.py`:

| Piece | Where it is |
|---|---|
| Forma GATT UUIDs + start/stop | `forma_due.py` top constants |
| 14-bit decode `((b1 & 0x3F) << 8) \| b0` | `FormaDue._decode` |
| Channel split `b1 & 0x40`, use one channel | `Bridge.on_due_sample` |
| Piecewise calibration | `counts_to_kg()` + `calibration.json` |
| Progressor service/char UUIDs, opcodes | `tindeq_bridge.py` top constants |
| Weight notification TLV `[0x01, len, float32 kg, uint32 us]` | `Bridge._send_weight` |
| Opcode 112 must stay unanswered | `Bridge.on_write` |

Calibration points can be hardcoded as a small array; no filesystem needed.

## Option B — Android foreground service

Possible but awkward.

**Dealbreaker:** Android has no BLE loopback — a phone cannot connect to its own
`BluetoothGattServer`. So the bridge service and the Tindeq app **cannot run on the same
phone**. You need phone A bridging and phone B/tablet running Tindeq.

Also needs: a foreground service with persistent notification, battery-optimisation
exemption, `BLUETOOTH_SCAN`/`BLUETOOTH_CONNECT`/`BLUETOOTH_ADVERTISE` permissions, and it
will still be fought by OEM background killers on Samsung/Xiaomi.

Only worth it if the bridge lives on a spare phone you already own.

## Prior art
[szbeni/forcegauge](https://github.com/szbeni/forcegauge) advertises as a Tindeq Progressor
from an ESP32. It generates its own data from an HX711 rather than bridging another BLE
device, so the dual-role central+peripheral part is the new work here.

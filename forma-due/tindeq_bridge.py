#!/usr/bin/env python3
"""Forma Due -> Tindeq Progressor bridge.

Connects to the Forma Due as a BLE *central*, and simultaneously advertises this
machine as a BLE *peripheral* implementing the Tindeq Progressor GATT API, so any
Tindeq-compatible app (phone, tablet, another computer) can use the Forma Due.

    python tindeq_bridge.py

Requires a calibration.json (run calibrate.py first) or it will report raw counts
as if they were kg.
"""
import asyncio, struct, sys, time

from bless import (BlessServer, GATTCharacteristicProperties,
                   GATTAttributePermissions)
from forma_due import FormaDue

# ---- Tindeq Progressor GATT ------------------------------------------------
PROG_SVC  = "7e4e1701-1ea6-40c9-9dcc-13d34ffead57"
PROG_DATA = "7e4e1702-1ea6-40c9-9dcc-13d34ffead57"   # notify
PROG_CTRL = "7e4e1703-1ea6-40c9-9dcc-13d34ffead57"   # write

CMD_TARE_SCALE            = 100
CMD_START_WEIGHT_MEAS     = 101
CMD_STOP_WEIGHT_MEAS      = 102
CMD_START_PEAK_RFD_MEAS   = 103
CMD_START_PEAK_RFD_SERIES = 104
CMD_ADD_CALIB_POINT       = 105
CMD_SAVE_CALIB            = 106
CMD_GET_APP_VERSION       = 107
CMD_GET_ERROR_INFO        = 108
CMD_CLR_ERROR_INFO        = 109
CMD_ENTER_SLEEP           = 110
CMD_GET_BATTERY_VOLTAGE   = 111
# 112 (0x70) is sent by the current Tindeq Android app but is not in the published
# API (which stops at 111). It appears to be a DFU / firmware-version probe: the app
# logs DFU errors when it goes unanswered, then connects and streams normally.
# We deliberately do NOT reply -- a fabricated response risks the app trying to push
# a Progressor firmware update to hardware that is not a Progressor.
CMD_DFU_PROBE_UNDOCUMENTED = 112

RES_CMD_RESPONSE    = 0x00
RES_WEIGHT_MEAS     = 0x01
RES_RFD_PEAK        = 0x02
RES_RFD_PEAK_SERIES = 0x03
RES_LOW_PWR_WARNING = 0x04

FW_VERSION = b"1.2.3.4"
ADV_NAME = "Progressor_1234"


class Bridge:
    def __init__(self):
        self.server = None
        self.due = None
        self.streaming = False
        self.tare_offset = 0.0
        self.t_start = time.time()
        self.latest = 0.0
        self._pending = []          # buffered (kg, us) samples
        self._batt_mv = 3800
        self._loop = None

    # ---- outbound: notify the Tindeq client ----
    def _notify(self, payload: bytes):
        try:
            ch = self.server.get_characteristic(PROG_DATA)
            ch.value = payload
            self.server.update_value(PROG_SVC, PROG_DATA)
        except Exception as e:
            print(f"  notify failed: {e}", file=sys.stderr)

    def _send_weight(self, kg, t_us):
        # RES_WEIGHT_MEAS: TLV header then (float32 kg, uint32 us)
        body = struct.pack("<fI", kg, t_us)
        self._notify(bytes([RES_WEIGHT_MEAS, len(body)]) + body)

    def _send_cmd_response(self, body: bytes):
        self._notify(bytes([RES_CMD_RESPONSE, len(body)]) + body)

    # ---- inbound: Forma Due samples ----
    def on_due_sample(self, t, kg, raw, tag, drift):
        if tag != 0x00:          # use one of the two interleaved channels (~28.6 Hz)
            return
        self.latest = kg
        if self.streaming:
            val = kg - self.tare_offset
            us = int((time.time() - self.t_start) * 1_000_000)
            self._send_weight(val, us)

    # ---- inbound: Tindeq control-point writes ----
    def on_write(self, characteristic, value, **kwargs):
        data = bytes(value)
        if not data:
            return
        op = data[0]
        print(f"  <- Tindeq cmd {op}", flush=True)
        if op == CMD_START_WEIGHT_MEAS:
            self.t_start = time.time()
            self.streaming = True
        elif op == CMD_STOP_WEIGHT_MEAS:
            self.streaming = False
        elif op == CMD_TARE_SCALE:
            self.tare_offset = self.latest
        elif op == CMD_GET_APP_VERSION:
            self._send_cmd_response(FW_VERSION)
        elif op == CMD_GET_BATTERY_VOLTAGE:
            self._send_cmd_response(struct.pack("<I", self._batt_mv))
        elif op == CMD_GET_ERROR_INFO:
            self._send_cmd_response(b"")
        elif op in (CMD_CLR_ERROR_INFO, CMD_SAVE_CALIB, CMD_ADD_CALIB_POINT):
            pass
        elif op == CMD_ENTER_SLEEP:
            print("  (client asked to sleep -- ignoring)")
        elif op == CMD_DFU_PROBE_UNDOCUMENTED:
            print("  (opcode 112 DFU probe -- deliberately unanswered, see note above)")
        else:
            print(f"  (unhandled opcode {op}, payload={data.hex()} -- not replying)")

    def on_read(self, characteristic, **kwargs):
        return characteristic.value or b""

    async def run(self):
        self._loop = asyncio.get_running_loop()

        print("Connecting to Forma Due...")
        self.due = FormaDue()
        await self.due.connect()
        info = await self.due.info()
        print(f"  fw={info['firmware']} sn={info['serial']} batt={info['battery_pct']}%")
        if self.due.cal.get("counts_per_kg", 1.0) == 1.0:
            print("  !! UNCALIBRATED -- values will be raw counts, not kg."
                  "  Run: python calibrate.py <known_kg>")
        self._batt_mv = int(3000 + (info['battery_pct'] or 100) / 100 * 1200)
        self.due.on_sample = self.on_due_sample
        await self.due.stream()
        await asyncio.sleep(1.0)
        await self.due.tare(1.5)
        print("  tared, streaming.")

        print(f"\nStarting Tindeq Progressor peripheral as {ADV_NAME!r}...")
        self.server = BlessServer(name=ADV_NAME, loop=self._loop)
        self.server.read_request_func = self.on_read
        self.server.write_request_func = self.on_write
        await self.server.add_new_service(PROG_SVC)
        await self.server.add_new_characteristic(
            PROG_SVC, PROG_DATA,
            GATTCharacteristicProperties.read | GATTCharacteristicProperties.notify,
            None, GATTAttributePermissions.readable)
        await self.server.add_new_characteristic(
            PROG_SVC, PROG_CTRL,
            GATTCharacteristicProperties.write | GATTCharacteristicProperties.write_without_response,
            None, GATTAttributePermissions.writeable)
        await self.server.start()
        print(f"  advertising service {PROG_SVC}")
        print("\nBridge live. Open your Tindeq-compatible app and connect to "
              f"{ADV_NAME!r}.  Ctrl-C to stop.\n")

        try:
            while True:
                await asyncio.sleep(1.0)
                state = "streaming" if self.streaming else "idle"
                print(f"\r  [{state}] latest {self.latest - self.tare_offset:7.2f}  ",
                      end="", flush=True)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            print("\nshutting down...")
            try: await self.server.stop()
            except Exception: pass
            await self.due.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(Bridge().run())
    except KeyboardInterrupt:
        pass

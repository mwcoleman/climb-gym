"""Forma Due (Forma Training Pty Ltd) BLE force-gauge driver.

Protocol reverse-engineered 2026-10-10 -- see PROTOCOL.md.
"""
import asyncio, json, os, struct, time
from bleak import BleakClient, BleakScanner

NAME_PREFIX = "Forma#"
SVC_MAIN  = "72d06610-1ea5-4ec7-8691-959b38283571"
CH_CTRL   = "c8770637-1739-4677-b3aa-ca4bf61608a7"   # 1 byte: 01 = stream on, 00 = off
CH_DATA   = "00767e89-b02b-487f-b636-9ccbd1e6acac"   # 3-byte notifications
CH_RATE   = "ab27449b-448e-44fd-b587-624890f82b16"   # 0x1e = 30 (Hz per channel), read-only
CH_CAL1   = "66e178e3-58d6-4253-a75b-30a754b1f431"   # floats 1800000.0 / 1500000.0 + u16 cfg
CH_CAL2   = "b6101851-e548-40bc-8ee0-ba6f4a8ae545"   # floats 1.775 / 1.79 + u16 cfg
CH_INFO   = "48c99f3c-833a-4148-8cff-6938fc08a8f3"
CH_BATT   = "00002a19-0000-1000-8000-00805f9b34fb"

CAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibration.json")
DEFAULT_CAL = {"counts_per_kg": 1.0, "note": "UNCALIBRATED - run calibrate.py"}


def load_cal(path=CAL_FILE):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_CAL)


def counts_to_kg(counts, cal):
    """Convert raw counts to kg.

    Uses the measured staircase points with piecewise-linear interpolation inside
    the calibrated range, and extrapolates beyond it with the nearest segment's
    slope. Falls back to a single counts_per_kg scale if no points are present.
    """
    pts = cal.get("calibration_points_kg_counts")
    if not pts or len(pts) < 2:
        return counts / cal.get("counts_per_kg", 1.0)
    pts = sorted((float(c), float(k)) for k, c in pts)      # (counts, kg)
    if counts <= pts[0][0]:
        (c0, k0), (c1, k1) = pts[0], pts[1]
    elif counts >= pts[-1][0]:
        (c0, k0), (c1, k1) = pts[-2], pts[-1]
    else:
        for i in range(1, len(pts)):
            if counts <= pts[i][0]:
                (c0, k0), (c1, k1) = pts[i - 1], pts[i]
                break
    if c1 == c0:
        return k0
    return k0 + (counts - c0) * (k1 - k0) / (c1 - c0)


class FormaDue:
    """Connect to a Forma Due and stream force samples.

    The device emits 3-byte notifications at ~57 Hz, strictly alternating between
    two interleaved channels identified by byte 1 (0x00 and 0x40), i.e. ~28.6 Hz
    each. Byte 0 is the tared force reading (0 at rest, saturates near 247).
    Byte 2 is a slowly drifting baseline/thermal indicator, not force.
    """

    CALIBRATED_MAX_KG = 30.0      # above this, kg values are extrapolated

    def __init__(self, address=None, cal=None):
        self.address = address
        self.cal = cal or load_cal()
        self._client = None
        self._tare = {0x00: 0.0, 0x40: 0.0}
        self.on_sample = None          # callback(t, kg, raw_counts)
        self._t0 = None

    @staticmethod
    async def discover(timeout=15.0):
        found = {}
        def cb(d, adv):
            n = adv.local_name or d.name or ""
            if n.startswith(NAME_PREFIX):
                found[d.address] = (n, d)
        s = BleakScanner(detection_callback=cb)
        await s.start()
        t0 = time.time()
        while time.time() - t0 < timeout and not found:
            await asyncio.sleep(0.4)
        await s.stop()
        return found

    async def connect(self):
        if self.address is None:
            found = await self.discover()
            if not found:
                raise RuntimeError("no Forma# device found (is it awake?)")
            self.address, dev = next(iter(found.values()))[1].address, None
        dev = await BleakScanner.find_device_by_address(self.address, timeout=20.0)
        if dev is None:
            raise RuntimeError(f"device {self.address} not found")
        self._client = BleakClient(dev, timeout=30.0)
        await self._client.connect()
        return self

    async def info(self):
        c = self._client
        async def rd(u):
            try: return bytes(await c.read_gatt_char(u))
            except Exception: return b""
        fw = (await rd("00002a26-0000-1000-8000-00805f9b34fb")).rstrip(b"\x00").decode("utf8", "replace")
        mfr = (await rd("00002a29-0000-1000-8000-00805f9b34fb")).rstrip(b"\x00").decode("utf8", "replace")
        sn = (await rd("00002a25-0000-1000-8000-00805f9b34fb"))[:16].rstrip(b"\x00").decode("utf8", "replace")
        batt = await rd(CH_BATT)
        return {"firmware": fw, "manufacturer": mfr, "serial": sn,
                "battery_pct": batt[0] if batt else None,
                "rate_hz": (await rd(CH_RATE))[:1].hex()}

    # Packet: [value_lo, flags, aux]
    #   value = ((flags & 0x3F) << 8) | value_lo      -- 14-bit, little-endian-ish
    #   channel tag = flags & 0x40                    -- two interleaved copies
    #   aux (byte 2) = slow drift indicator, not force
    VALUE_HI_MASK = 0x3F
    CHAN_MASK     = 0x40

    def _decode(self, data):
        """3-byte packet -> (channel_tag, value_counts, aux_byte)."""
        if len(data) != 3:
            return None
        lo, flags, aux = data[0], data[1], data[2]
        value = ((flags & self.VALUE_HI_MASK) << 8) | lo
        return flags & self.CHAN_MASK, value, aux

    async def stream(self, duration=None):
        """Start streaming. Samples go to self.on_sample."""
        c = self._client
        self._t0 = time.time()
        def handler(_, data):
            dec = self._decode(bytes(data))
            if dec is None:
                return
            tag, raw, drift = dec
            counts = raw - self._tare.get(tag, 0.0)
            kg = counts_to_kg(counts, self.cal)
            if self.on_sample:
                self.on_sample(time.time() - self._t0, kg, raw, tag, drift)
        await c.start_notify(CH_DATA, handler)
        await c.write_gatt_char(CH_CTRL, b"\x01", response=True)
        if duration:
            await asyncio.sleep(duration)
            await self.stop()

    async def stop(self):
        try:
            await self._client.write_gatt_char(CH_CTRL, b"\x00", response=True)
            await self._client.stop_notify(CH_DATA)
        except Exception:
            pass

    async def tare(self, seconds=1.5):
        """Average current readings per channel and use as zero."""
        acc = {0x00: [], 0x40: []}
        prev = self.on_sample
        self.on_sample = lambda t, kg, raw, tag, drift: acc.setdefault(tag, []).append(raw)
        await asyncio.sleep(seconds)
        self.on_sample = prev
        for tag, vals in acc.items():
            if vals:
                self._tare[tag] = sum(vals) / len(vals)
        return dict(self._tare)

    async def disconnect(self):
        await self.stop()
        if self._client:
            await self._client.disconnect()

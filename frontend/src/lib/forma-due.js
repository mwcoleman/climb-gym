// Climbing fork: the Forma Due force gauge, read straight over Web Bluetooth.
//
// Protocol reverse-engineered in forma-due/PROTOCOL.md: write 0x01 to the control characteristic
// to stream, then 3-byte notifications arrive at ~57 Hz, alternating between two load cells.
// The decode and the calibration are pure functions so they can be tested; FormaDue is the thin
// browser wrapper around them.

export const SVC_MAIN = '72d06610-1ea5-4ec7-8691-959b38283571'
export const CH_CTRL = 'c8770637-1739-4677-b3aa-ca4bf61608a7'   // 01 = stream on, 00 = off
export const CH_DATA = '00767e89-b02b-487f-b636-9ccbd1e6acac'   // 3-byte notifications
export const NAME_PREFIX = 'Forma#'

// This unit's 4-point staircase (serial CC4533DB5110, forma-due/calibration.json): [kg, counts].
export const DEFAULT_CAL = [[0, 0], [10, 86.04], [20, 180.92], [30, 279.17]]

/**
 * One 3-byte packet → { channel, value } or null.
 * Byte 1 is NOT a pure channel tag: bits 0-5 are the value's high bits, only bit 6 is the
 * channel. Filtering on byte1 === 0 silently drops every sample above 255 counts.
 */
export function decodePacket(bytes) {
  if (!bytes || bytes.length !== 3) return null
  const lo = bytes[0], flags = bytes[1]
  return { channel: flags & 0x40, value: ((flags & 0x3F) << 8) | lo }
}

/**
 * Counts → kg by piecewise-linear interpolation through the calibration points, extrapolating
 * outside them with the nearest segment's slope (above 30 kg is extrapolated).
 */
export function countsToKg(counts, cal = DEFAULT_CAL) {
  const pts = cal.map(([kg, c]) => [c, kg]).sort((a, b) => a[0] - b[0])
  let i = 1
  while (i < pts.length - 1 && counts > pts[i][0]) i++
  const [c0, k0] = pts[i - 1], [c1, k1] = pts[i]
  if (c1 === c0) return k0
  return k0 + (counts - c0) * (k1 - k0) / (c1 - c0)
}

/**
 * Split a force trace into hangs. samples: [{ t (seconds), kg }], in time order.
 * A hang starts when force rises to `start` kg and ends when it drops below `end` kg; anything
 * shorter than `minSec` is a bump, not a hang. Hysteresis (start > end) stops noise at the
 * threshold from splitting one hang into several.
 * → [{ start, end, duration, peak, avg }], seconds and kg, rounded to 0.1.
 */
export function detectHangs(samples, { start = 5, end = 3, minSec = 1 } = {}) {
  const out = []
  let cur = null
  const close = last => {
    const duration = last.t - cur.start
    if (duration >= minSec) {
      out.push({
        start: r1(cur.start), end: r1(last.t), duration: r1(duration),
        peak: r1(cur.peak), avg: r1(cur.sum / cur.n)
      })
    }
    cur = null
  }
  let prev = null
  for (const s of samples) {
    if (!cur && s.kg >= start) cur = { start: s.t, peak: s.kg, sum: 0, n: 0 }
    if (cur) {
      if (s.kg < end) { close(prev || s); prev = s; continue }
      cur.peak = Math.max(cur.peak, s.kg)
      cur.sum += s.kg; cur.n++
    }
    prev = s
  }
  if (cur && prev) close(prev)
  return out
}

const r1 = x => Math.round(x * 10) / 10

/**
 * Browser driver. onSample({ t, kg, raw, channel }) fires per packet; one channel is enough
 * (both read the same to within a count), so only channel 0x00 is reported.
 */
export class FormaDue {
  constructor({ cal = DEFAULT_CAL, onSample, onDisconnect } = {}) {
    this.cal = cal
    this.onSample = onSample
    this.onDisconnect = onDisconnect
    this.tare = 0
    this._ctrl = null
    this._data = null
    this._t0 = 0
    this._tareBuf = null
  }

  static supported() {
    return typeof navigator !== 'undefined' && !!navigator.bluetooth
  }

  async connect() {
    const device = await navigator.bluetooth.requestDevice({
      filters: [{ namePrefix: NAME_PREFIX }],
      optionalServices: [SVC_MAIN]
    })
    this.device = device
    device.addEventListener('gattserverdisconnected', () => this.onDisconnect?.())
    const server = await device.gatt.connect()
    const svc = await server.getPrimaryService(SVC_MAIN)
    this._ctrl = await svc.getCharacteristic(CH_CTRL)
    this._data = await svc.getCharacteristic(CH_DATA)
    this._data.addEventListener('characteristicvaluechanged', e => this._onPacket(e.target.value))
    await this._data.startNotifications()
    this._t0 = performance.now()
    await this._ctrl.writeValueWithResponse(Uint8Array.of(1))
    return device.name
  }

  _onPacket(view) {
    const p = decodePacket(new Uint8Array(view.buffer, view.byteOffset, view.byteLength))
    if (!p || p.channel !== 0) return
    if (this._tareBuf) { this._tareBuf.push(p.value); return }
    const kg = countsToKg(p.value - this.tare, this.cal)
    this.onSample?.({ t: (performance.now() - this._t0) / 1000, kg, raw: p.value })
  }

  /** Average the unloaded reading for `ms` and use it as zero. */
  async zero(ms = 1500) {
    this._tareBuf = []
    await new Promise(r => setTimeout(r, ms))
    const buf = this._tareBuf
    this._tareBuf = null
    if (buf.length) this.tare = buf.reduce((a, b) => a + b, 0) / buf.length
    return this.tare
  }

  async disconnect() {
    try { await this._ctrl?.writeValueWithResponse(Uint8Array.of(0)) } catch { /* already gone */ }
    try { this.device?.gatt?.disconnect() } catch { /* already gone */ }
  }
}

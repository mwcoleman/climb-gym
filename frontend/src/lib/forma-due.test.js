import { describe, it, expect } from 'vitest'
import { decodePacket, countsToKg, detectHangs, DEFAULT_CAL } from './forma-due.js'

describe('decodePacket', () => {
  it('reads byte 1 bits 0-5 as the high bits, not as part of the channel tag', () => {
    // The 254 → 260 wrap caught in a slow ramp (forma-due/PROTOCOL.md).
    expect(decodePacket([254, 0x00, 0x4d])).toEqual({ channel: 0x00, value: 254 })
    expect(decodePacket([4, 0x41, 0x4d])).toEqual({ channel: 0x40, value: 260 })
    expect(decodePacket([7, 0x01, 0x4d])).toEqual({ channel: 0x00, value: 263 })
  })

  it('ignores byte 2 (a drift indicator, not force)', () => {
    expect(decodePacket([10, 0, 0x00]).value).toBe(decodePacket([10, 0, 0xff]).value)
  })

  it('reaches the full 14 bits', () => {
    expect(decodePacket([0xff, 0x7f, 0]).value).toBe(16383)
    expect(decodePacket([0x71, 0x02, 0]).value).toBe(625)
  })

  it('refuses a packet that is not 3 bytes', () => {
    expect(decodePacket([1, 2])).toBeNull()
    expect(decodePacket(null)).toBeNull()
  })
})

describe('countsToKg', () => {
  it('hits every calibration point exactly', () => {
    for (const [kg, c] of DEFAULT_CAL) expect(countsToKg(c)).toBeCloseTo(kg, 6)
  })

  it('interpolates within a segment', () => {
    expect(countsToKg(43.02)).toBeCloseTo(5, 6)
  })

  it('extrapolates above 30 kg with the 20-30 kg slope', () => {
    // PROTOCOL.md cross-checks: ramp peak 625 counts ≈ 65.2 kg, bodyweight hang 573 ≈ 59.9 kg.
    expect(countsToKg(625)).toBeCloseTo(65.2, 1)
    expect(countsToKg(573)).toBeCloseTo(59.9, 1)
  })

  it('goes slightly negative below zero rather than clamping (an untared offset shows up)', () => {
    expect(countsToKg(-8.604)).toBeCloseTo(-1, 6)
  })
})

describe('detectHangs', () => {
  const trace = (pieces, hz = 10) => {
    const out = []
    let t = 0
    for (const [kg, sec] of pieces) for (let i = 0; i < sec * hz; i++) { out.push({ t, kg }); t = Math.round((t + 1 / hz) * 1000) / 1000 }
    return out
  }

  it('finds a 7:3 repeater set as separate hangs', () => {
    const hangs = detectHangs(trace([[0, 1], [20, 7], [0, 3], [22, 7], [0, 3], [18, 7], [0, 1]]))
    expect(hangs).toHaveLength(3)
    expect(hangs.map(h => h.peak)).toEqual([20, 22, 18])
    for (const h of hangs) expect(h.duration).toBeCloseTo(6.9, 1)
  })

  it('does not split one hang on noise between the end and start thresholds', () => {
    const hangs = detectHangs(trace([[0, 1], [10, 3], [4, 0.3], [10, 3], [0, 1]]))
    expect(hangs).toHaveLength(1)
  })

  it('drops bumps shorter than minSec', () => {
    expect(detectHangs(trace([[0, 1], [15, 0.5], [0, 1]]))).toEqual([])
  })

  it('closes a hang still running at the end of the trace', () => {
    const [h] = detectHangs(trace([[0, 1], [30, 5]]))
    expect(h.peak).toBe(30)
    expect(h.avg).toBe(30)
  })
})

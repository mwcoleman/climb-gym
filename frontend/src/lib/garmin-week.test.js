import { describe, it, expect } from 'vitest'
import { recentSessions, totalMinutes, typeOf, detailLine } from './garmin-week.js'

const doc = {
  activities: {
    1: { date: '2026-10-09', type: 'bouldering', name: 'Too old', duration_min: 60 },
    2: { date: '2026-10-10', start: '2026-10-10 18:00:00', type: 'bouldering', name: 'Edge of window', duration_min: 90 },
    3: { date: '2026-10-14', start: '2026-10-14 07:00:00', type: 'strength_training', name: 'AM', duration_min: 45 },
    4: { date: '2026-10-14', start: '2026-10-14 19:00:00', type: 'indoor_climbing', name: 'PM', duration_min: 120 },
    5: { date: '2026-10-17', type: 'bouldering', name: 'Future (clock skew)', duration_min: 10 }
  }
}

describe('recentSessions', () => {
  it('keeps the last 7 days including today, newest first by start time', () => {
    expect(recentSessions(doc, '2026-10-16').map(a => a.name)).toEqual(['PM', 'AM', 'Edge of window'])
  })
  it('carries the activity id', () => {
    expect(recentSessions(doc, '2026-10-16')[0].id).toBe('4')
  })
  it('copes with an empty or malformed document', () => {
    expect(recentSessions({ activities: {} }, '2026-10-16')).toEqual([])
    expect(recentSessions(null, '2026-10-16')).toEqual([])
    expect(recentSessions({ activities: { x: { name: 'no date' } } }, '2026-10-16')).toEqual([])
  })
})

describe('totalMinutes / typeOf', () => {
  it('sums durations, ignoring junk', () => {
    expect(totalMinutes([{ duration_min: 45 }, { duration_min: 120 }, {}])).toBe(165)
  })
  it('labels known types and falls back to the typeKey', () => {
    expect(typeOf('bouldering').label).toBe('Bouldering')
    expect(typeOf('hiit').label).toBe('hiit')
  })
})

describe('detailLine', () => {
  it('summarises a climbing session', () => {
    expect(detailLine({ details: { climbs: [{}, {}, {}, {}, {}], attempted: 5, sent: 3, max_sent: '6B+' } })).toBe('3/5 sent · top 6B+')
    expect(detailLine({ details: { climbs: [{}], attempted: 1, sent: 0, max_sent: null } })).toBe('0/1 sent')
    expect(detailLine({ details: { climbs: [], attempted: 0, sent: 0 } })).toBe('')
  })
  it('lists distinct strength exercises, at most three', () => {
    const sets = ['WEIGHTED_PULL_UP', 'BARBELL_BENCH_PRESS', 'WEIGHTED_PULL_UP', 'LAT_PULLDOWN', 'DEADLIFT'].map(exercise => ({ exercise }))
    expect(detailLine({ details: { sets } })).toBe('Weighted pull up · Barbell bench press · Lat pulldown +1')
  })
  it('is empty without details', () => {
    expect(detailLine({})).toBe('')
  })
})

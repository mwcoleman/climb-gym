// Climbing fork: turns the garmin-sync document (GET /api/external/garmin) into the Home card's
// rows. Pure, so the date window and the labels are tested rather than eyeballed.

const TYPES = {
  bouldering: { label: 'Bouldering', icon: 'pullup' },
  indoor_climbing: { label: 'Climbing', icon: 'pullup' },
  rock_climbing: { label: 'Climbing', icon: 'pullup' },
  strength_training: { label: 'Strength', icon: 'dumbbell' }
}

export const typeOf = key => TYPES[key] || { label: String(key || '').replace(/_/g, ' '), icon: 'figureRun' }

/** Sessions on or after `days - 1` days before `todayIso`, newest first. */
export function recentSessions(doc, todayIso, days = 7) {
  const acts = doc && typeof doc.activities === 'object' && doc.activities ? doc.activities : {}
  const from = new Date(todayIso + 'T00:00:00Z')
  from.setUTCDate(from.getUTCDate() - (days - 1))
  const fromIso = from.toISOString().slice(0, 10)
  return Object.entries(acts)
    .map(([id, a]) => ({ id, ...a }))
    .filter(a => typeof a.date === 'string' && a.date >= fromIso && a.date <= todayIso)
    .sort((a, b) => (b.start || b.date).localeCompare(a.start || a.date))
}

/** Summary line: "3 sessions · 4 h 10 min". */
export function totalMinutes(sessions) {
  return sessions.reduce((n, a) => n + (Number(a.duration_min) || 0), 0)
}

const pretty = name => {
  const s = String(name || '').toLowerCase().replace(/_/g, ' ')
  return s.charAt(0).toUpperCase() + s.slice(1)
}

/**
 * The one-line detail under a session: "3/5 sent · top 6B+" for a climb, the distinct exercises
 * in order for a strength session. Empty when garmin-sync had nothing more than the summary.
 */
export function detailLine(a) {
  const d = a?.details || {}
  if (Array.isArray(d.climbs)) {
    if (!d.climbs.length) return ''
    return `${d.sent}/${d.attempted} sent` + (d.max_sent ? ` · top ${d.max_sent}` : '')
  }
  if (Array.isArray(d.sets)) {
    const names = [...new Set(d.sets.map(s => s.exercise).filter(Boolean))]
    return names.slice(0, 3).map(pretty).join(' · ') + (names.length > 3 ? ` +${names.length - 3}` : '')
  }
  return ''
}

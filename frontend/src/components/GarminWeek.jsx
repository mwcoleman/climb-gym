// Climbing fork: "From your Fenix this week" — the sessions garmin-sync pulled from Garmin
// Connect, read through GET /api/external/garmin. Renders nothing for a guest, a profile the
// server won't share the file with, or an instance with no sync running yet.
import { useEffect, useState } from 'react'
import { api } from '../lib/api.js'
import { recentSessions, totalMinutes, typeOf, detailLine } from '../lib/garmin-week.js'
import { fmtDate, todayISO } from '../lib/format.js'
import { t } from '../lib/i18n.js'
import Icon from './Icon.jsx'

const mins = m => (m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`)

export default function GarminWeek() {
  const [doc, setDoc] = useState(null)

  useEffect(() => {
    let live = true
    api('/api/external/garmin').then(d => { if (live) setDoc(d) }).catch(() => { if (live) setDoc(null) })
    return () => { live = false }
  }, [])

  if (!doc) return null
  const sessions = recentSessions(doc, todayISO())

  return (
    <div className="card">
      <div className="row between" style={{ marginBottom: 6 }}>
        <h2 style={{ margin: 0 }}>{t('From your Fenix this week')}</h2>
        {!!sessions.length && <span className="dim small">{sessions.length} · {mins(totalMinutes(sessions))}</span>}
      </div>
      {!sessions.length
        ? <div className="muted small">{doc.last_sync ? t('No sessions in the last 7 days.') : t('Nothing synced yet.')}</div>
        : sessions.map(a => {
          const ty = typeOf(a.type)
          return (
            <div key={a.id} className="row" style={{ gap: 9, padding: '6px 0' }}>
              <span className="lrow-i" style={{ background: a.type === 'strength_training' ? 'var(--blue)' : 'var(--orange)' }}><Icon name={ty.icon} /></span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name || t(ty.label)}</div>
                <div className="muted small">{fmtDate(a.date)} · {detailLine(a) || t(ty.label)}</div>
              </div>
              <span className="small" style={{ fontVariantNumeric: 'tabular-nums' }}>{mins(Number(a.duration_min) || 0)}</span>
            </div>
          )
        })}
    </div>
  )
}

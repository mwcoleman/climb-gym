// Climbing fork: live hangboard force from the Forma Due (lib/forma-due.js), with each hang
// picked out of the trace automatically. Session-only for now — nothing here is saved to the
// profile; reloading the page starts a fresh session.
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FormaDue, detectHangs } from '../lib/forma-due.js'
import { t } from '../lib/i18n.js'
import Icon from '../components/Icon.jsx'
import { Button } from '../components/ui.jsx'

const WINDOW_SEC = 15   // how much trace the chart shows

function Trace({ samples, peak }) {
  const W = 320, H = 120
  if (samples.length < 2) return <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: H }} />
  const tEnd = samples[samples.length - 1].t
  const top = Math.max(10, peak * 1.1)
  const pts = samples.map(s => `${((s.t - (tEnd - WINDOW_SEC)) / WINDOW_SEC * W).toFixed(1)},${(H - Math.max(0, s.kg) / top * H).toFixed(1)}`).join(' ')
  return (
    <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: '100%', height: H, display: 'block' }}>
      <line x1="0" x2={W} y1={H - 5 / top * H} y2={H - 5 / top * H} stroke="var(--label-3)" strokeDasharray="3 4" strokeWidth="1" />
      <polyline points={pts} fill="none" stroke="var(--accent)" strokeWidth="2" vectorEffect="non-scaling-stroke" />
    </svg>
  )
}

export default function Hang() {
  const nav = useNavigate()
  const due = useRef(null)
  const all = useRef([])
  const [status, setStatus] = useState('idle')   // idle | connecting | zeroing | live | lost
  const [, setTick] = useState(0)

  useEffect(() => {
    let raf
    const loop = () => { setTick(n => n + 1); raf = requestAnimationFrame(loop) }
    raf = requestAnimationFrame(loop)
    return () => { cancelAnimationFrame(raf); due.current?.disconnect() }
  }, [])

  const connect = async () => {
    setStatus('connecting')
    const d = new FormaDue({
      onSample: s => all.current.push(s),
      onDisconnect: () => setStatus('lost')
    })
    try {
      await d.connect()
      due.current = d
      setStatus('zeroing')
      await d.zero()
      setStatus('live')
    } catch (e) {
      setStatus(e?.name === 'NotFoundError' ? 'idle' : 'lost')
    }
  }
  const zero = async () => { setStatus('zeroing'); await due.current.zero(); setStatus('live') }
  const reset = () => { all.current = [] }

  const samples = all.current
  const last = samples[samples.length - 1]
  const tEnd = last?.t ?? 0
  const recent = samples.filter(s => s.t >= tEnd - WINDOW_SEC)
  const hangs = detectHangs(samples)
  const peak = hangs.reduce((m, h) => Math.max(m, h.peak), 0)
  const live = status === 'live'

  return (
    <div className="narrow">
      <div className="hdr">
        <div className="row" style={{ gap: 8 }}>
          <button className="iconbtn" onClick={() => nav(-1)} aria-label={t('Back')}><Icon name="chevronLeft" /></button>
          <div><h1>{t('Hangboard')}</h1><div className="sub">Forma Due</div></div>
        </div>
      </div>

      {!FormaDue.supported() && (
        <div className="card muted small">{t('This browser has no Web Bluetooth. Use Chrome on a Mac, Android or Windows device.')}</div>
      )}

      <div className="card">
        <div className="row" style={{ alignItems: 'baseline', gap: 8 }}>
          <div className="big" style={{ fontSize: 64, fontVariantNumeric: 'tabular-nums' }}>{live && last ? last.kg.toFixed(1) : '–'}</div>
          <span className="muted">kg</span>
          {!!peak && <span className="small" style={{ marginInlineStart: 'auto', color: 'var(--yellow)' }}>{t('Peak')} {peak.toFixed(1)} kg</span>}
        </div>
        <Trace samples={recent} peak={Math.max(peak, ...recent.map(s => s.kg))} />
        <div className="muted small" style={{ marginTop: 6 }}>
          {status === 'idle' && t('Wake the gauge, then connect.')}
          {status === 'connecting' && t('Connecting…')}
          {status === 'zeroing' && t('Zeroing — hands off the gauge…')}
          {status === 'live' && t('Pull! Each hang over 5 kg is logged below.')}
          {status === 'lost' && t('Disconnected. Wake the gauge and connect again.')}
        </div>
        <div className="row" style={{ gap: 8, marginTop: 10 }}>
          {!live && <Button variant="primary" icon="bolt" disabled={status === 'connecting' || status === 'zeroing' || !FormaDue.supported()} onClick={connect}>{t('Connect')}</Button>}
          {live && <Button icon="reset" onClick={zero}>{t('Zero')}</Button>}
          {!!samples.length && <Button variant="ghost" icon="trash" onClick={reset}>{t('Clear')}</Button>}
        </div>
      </div>

      <div className="card">
        <h2 style={{ marginTop: 0 }}>{t('Hangs')}</h2>
        {!hangs.length ? <div className="muted small">{t('None yet.')}</div> : (
          <table className="small" style={{ width: '100%', fontVariantNumeric: 'tabular-nums', borderCollapse: 'collapse' }}>
            <thead><tr className="muted" style={{ textAlign: 'end' }}>
              <th style={{ textAlign: 'start' }}>#</th><th>{t('Time')}</th><th>{t('Peak')}</th><th>{t('Avg')}</th>
            </tr></thead>
            <tbody>
              {hangs.map((h, i) => (
                <tr key={i} style={{ textAlign: 'end' }}>
                  <td style={{ textAlign: 'start', padding: '4px 0' }}>{i + 1}</td>
                  <td>{h.duration.toFixed(1)} s</td><td>{h.peak.toFixed(1)} kg</td><td>{h.avg.toFixed(1)} kg</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

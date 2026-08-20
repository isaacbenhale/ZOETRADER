import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const POLL_MS = 1500

export default function ApprovalPanel() {
  const [status, setStatus] = useState(null)
  const [equity, setEquity] = useState(10000)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState(null)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    const refresh = () => {
      api
        .approvalStatus()
        .then((data) => mounted.current && setStatus(data))
        .catch(() => {})
    }
    refresh()
    const interval = setInterval(refresh, POLL_MS)
    return () => {
      mounted.current = false
      clearInterval(interval)
    }
  }, [])

  const act = async (name, action) => {
    setBusy(name)
    setError(null)
    try {
      const result = await action()
      const fresh = await api.approvalStatus()
      setStatus(fresh)
      return result
    } catch (err) {
      setError(err.message)
      return null
    } finally {
      setBusy(null)
    }
  }

  const running = status?.running ?? false
  const pending = status?.pending_decision
  const killed = status?.kill_switch ?? false

  return (
    <section className="panel">
      <h2>Approbation MANUAL</h2>
      <p className="hint">
        Ces boutons font exactement la meme chose que ceux du panneau MT5 &mdash; les deux ecrivent dans le meme
        fichier de commande. APPROVE envoie reellement l&apos;ordre deja valide par le Risk Engine. AUTO reste
        inaccessible ici.
      </p>

      {error && <p className="error">{error}</p>}
      {status?.start_error && <p className="error">Echec du demarrage : {status.start_error}</p>}

      {killed && (
        <p className="banner" style={{ borderColor: 'var(--danger)', background: 'var(--danger-bg)' }}>
          KILL SWITCH engage : plus aucune nouvelle proposition tant que RESUME n&apos;est pas clique.
        </p>
      )}

      {!running ? (
        <div className="actions-row">
          <label>
            Equity
            <input type="number" value={equity} onChange={(event) => setEquity(Number(event.target.value))} />
          </label>
          <button
            disabled={busy !== null}
            onClick={() => act('start', () => api.approvalStart({ equity, candle_count: 200 }))}
          >
            Demarrer la boucle
          </button>
        </div>
      ) : (
        <div className="actions-row">
          <button disabled={busy !== null} onClick={() => act('stop', () => api.approvalStop())}>
            Arreter la boucle
          </button>
        </div>
      )}

      {running && (
        <div className="details-grid" style={{ marginBottom: 12 }}>
          <div>
            <strong>Etat</strong>
            <span>{killed ? 'gele (kill switch)' : 'en cours'}</span>
          </div>
          <div>
            <strong>Dernier resultat</strong>
            <span>{status?.last_outcome ?? '-'}</span>
          </div>
        </div>
      )}

      {pending ? (
        <div className="details-grid" style={{ marginBottom: 12 }}>
          <div className="details-wide">
            <strong>Proposition en attente</strong>
            <span>
              {pending.final_action} {pending.signal?.instrument} &mdash; {pending.signal?.strategy} (score{' '}
              {pending.signal?.setup_score})
            </span>
          </div>
          <div>
            <strong>Entree</strong>
            <span>{pending.signal?.entry ?? '-'}</span>
          </div>
          <div>
            <strong>SL</strong>
            <span>{pending.signal?.proposed_sl ?? '-'}</span>
          </div>
          <div>
            <strong>TP</strong>
            <span>{pending.signal?.proposed_tp ?? '-'}</span>
          </div>
        </div>
      ) : (
        running && <p className="hint">Aucune proposition en attente pour l&apos;instant.</p>
      )}

      <div className="actions-row">
        <button
          disabled={busy !== null || !pending}
          onClick={() => act('approve', () => api.approvalApprove())}
        >
          APPROVE
        </button>
        <button disabled={busy !== null || !pending} onClick={() => act('reject', () => api.approvalReject())}>
          REJECT
        </button>
        <button disabled={busy !== null} onClick={() => act('pause', () => api.approvalPause())}>
          PAUSE
        </button>
        <button disabled={busy !== null} onClick={() => act('kill', () => api.approvalKill())}>
          KILL
        </button>
        <button disabled={busy !== null} onClick={() => act('resume', () => api.approvalResume())}>
          RESUME
        </button>
      </div>
    </section>
  )
}

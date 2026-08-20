import { useState } from 'react'
import { api } from '../api'

export default function ActionsPanel({ onScanned, onBacktested }) {
  const [busy, setBusy] = useState(null)
  const [log, setLog] = useState([])
  const [mode, setMode] = useState('MONITORING')
  const [equity, setEquity] = useState(10000)
  const [candleCount, setCandleCount] = useState(500)
  const [lookaheadBars, setLookaheadBars] = useState(20)

  const run = async (name, action) => {
    setBusy(name)
    try {
      const result = await action()
      pushLog(`${name} OK`, result)
      return result
    } catch (err) {
      pushLog(`${name} ECHEC`, { error: err.message })
      return null
    } finally {
      setBusy(null)
    }
  }

  const pushLog = (title, payload) => {
    setLog((previous) => [{ id: Date.now(), title, payload }, ...previous].slice(0, 8))
  }

  return (
    <section className="panel">
      <h2>Lancer</h2>
      <p className="hint">
        Ces boutons declenchent les memes operations que la CLI. Aucune ne peut approuver un ordre ni activer AUTO
        &mdash; ca reste dans MT5.
      </p>

      <div className="actions-row">
        <button disabled={busy !== null} onClick={() => run('Verifier Config', () => api.bootstrap(mode))}>
          Verifier Config
        </button>
        <button disabled={busy !== null} onClick={() => run('healthcheck', () => api.healthcheck())}>
          Healthcheck
        </button>
      </div>

      <div className="actions-row">
        <label>
          Mode
          <select value={mode} onChange={(event) => setMode(event.target.value)}>
            <option value="MONITORING">MONITORING</option>
            <option value="MANUAL">MANUAL</option>
          </select>
        </label>
        <label>
          Equity
          <input type="number" value={equity} onChange={(event) => setEquity(Number(event.target.value))} />
        </label>
        <button
          disabled={busy !== null}
          onClick={() =>
            run('scan', () => api.scan({ mode, equity, candle_count: 200 })).then((result) => {
              if (result) onScanned(result)
            })
          }
        >
          Scan
        </button>
      </div>

      <div className="actions-row">
        <label>
          Bougies
          <input type="number" value={candleCount} onChange={(event) => setCandleCount(Number(event.target.value))} />
        </label>
        <label>
          Lookahead
          <input
            type="number"
            value={lookaheadBars}
            onChange={(event) => setLookaheadBars(Number(event.target.value))}
          />
        </label>
        <button
          disabled={busy !== null}
          onClick={() =>
            run('backtest', () =>
              api.backtest({ candle_count: candleCount, lookahead_bars: lookaheadBars }),
            ).then((result) => {
              if (result) onBacktested(result)
            })
          }
        >
          Backtest
        </button>
      </div>

      {busy && <p className="busy">{busy} en cours&hellip;</p>}

      <ul className="log">
        {log.map((entry) => (
          <li key={entry.id}>
            <strong>{entry.title}</strong>
            <pre>{JSON.stringify(entry.payload, null, 2)}</pre>
          </li>
        ))}
      </ul>
    </section>
  )
}

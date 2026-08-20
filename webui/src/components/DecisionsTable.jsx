import { Fragment, useState } from 'react'

export default function DecisionsTable({ decisions }) {
  const [expandedId, setExpandedId] = useState(null)

  return (
    <section className="panel">
      <h2>Decisions recentes</h2>
      {decisions.length === 0 ? (
        <p className="hint">Aucune decision journalisee pour l&apos;instant. Lance un scan.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Instrument</th>
                <th>Action</th>
                <th>Strategie</th>
                <th>Regime</th>
                <th>Score</th>
                <th>Entree</th>
                <th>SL</th>
                <th>TP</th>
                <th>RR attendu</th>
                <th>Verdict risque</th>
                <th>Cree le</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((decision) => {
                const signal = decision.signal ?? {}
                const risk = decision.risk ?? {}
                const isExpanded = expandedId === decision.decision_id
                return (
                  <Fragment key={decision.decision_id}>
                    <tr>
                      <td>{signal.instrument ?? '-'}</td>
                      <td className={`action-${(decision.final_action ?? '').toLowerCase()}`}>
                        {decision.final_action}
                      </td>
                      <td>{signal.strategy ?? '-'}</td>
                      <td>{signal.regime ?? '-'}</td>
                      <td>{signal.setup_score ?? '-'}</td>
                      <td>{fmt(signal.entry)}</td>
                      <td>{fmt(signal.proposed_sl)}</td>
                      <td>{fmt(signal.proposed_tp)}</td>
                      <td>{fmt(signal.expected_rr)}</td>
                      <td>{risk.verdict ?? '-'}</td>
                      <td>{decision.created_at ? new Date(decision.created_at).toLocaleString() : '-'}</td>
                      <td>
                        <button
                          className="link-button"
                          onClick={() => setExpandedId(isExpanded ? null : decision.decision_id)}
                        >
                          {isExpanded ? 'Masquer' : 'Details'}
                        </button>
                      </td>
                    </tr>
                    {isExpanded && (
                      <tr className="details-row" key={`${decision.decision_id}-details`}>
                        <td colSpan={12}>
                          <div className="details-grid">
                            <div>
                              <strong>Invalidation</strong>
                              <span>{fmt(signal.invalidation)}</span>
                            </div>
                            <div>
                              <strong>Risque / trade</strong>
                              <span>{risk.risk_per_trade_pct != null ? `${risk.risk_per_trade_pct}%` : '-'}</span>
                            </div>
                            <div>
                              <strong>Taille position</strong>
                              <span>{fmt(risk.position_size)}</span>
                            </div>
                            <div>
                              <strong>Perte max</strong>
                              <span>{fmt(risk.max_loss_amount)}</span>
                            </div>
                            <div className="details-wide">
                              <strong>Raisons du signal</strong>
                              <span>{(signal.reasons ?? []).join(', ') || '-'}</span>
                            </div>
                            <div className="details-wide">
                              <strong>Blockers signal</strong>
                              <span>{(signal.blockers ?? []).join(', ') || 'aucun'}</span>
                            </div>
                            <div className="details-wide">
                              <strong>Raisons risque</strong>
                              <span>{(risk.reasons ?? []).join(', ') || 'aucune'}</span>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function fmt(value) {
  if (value === null || value === undefined) return '-'
  return typeof value === 'number' ? value.toFixed(5).replace(/0+$/, '').replace(/\.$/, '') : String(value)
}

export default function DecisionsTable({ decisions }) {
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
                <th>Score</th>
                <th>Verdict risque</th>
                <th>Cree le</th>
              </tr>
            </thead>
            <tbody>
              {decisions.map((decision) => (
                <tr key={decision.decision_id}>
                  <td>{decision.signal?.instrument ?? '-'}</td>
                  <td className={`action-${(decision.final_action ?? '').toLowerCase()}`}>
                    {decision.final_action}
                  </td>
                  <td>{decision.signal?.strategy ?? '-'}</td>
                  <td>{decision.signal?.setup_score ?? '-'}</td>
                  <td>{decision.risk?.verdict ?? '-'}</td>
                  <td>{decision.created_at ? new Date(decision.created_at).toLocaleString() : '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

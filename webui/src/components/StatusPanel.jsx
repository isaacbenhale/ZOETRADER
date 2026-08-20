export default function StatusPanel({ status, error }) {
  const fields = status?.status_file ?? {}
  const journal = status?.journal ?? {}

  return (
    <section className="panel">
      <h2>Etat</h2>
      {error && <p className="error">{error}</p>}
      <div className="status-grid">
        <StatusField label="Statut" value={fields.status ?? '-'} />
        <StatusField label="Mode" value={fields.mode ?? '-'} />
        <StatusField label="Dernier signal" value={fields.signal ?? '-'} />
        <StatusField label="Strategie" value={fields.strategy ?? '-'} />
        <StatusField label="Regime" value={fields.regime ?? '-'} />
        <StatusField label="Score" value={fields.score ?? '-'} />
        <StatusField label="Entry" value={fields.entry ?? '-'} />
        <StatusField label="SL" value={fields.sl ?? '-'} />
        <StatusField label="TP" value={fields.tp ?? '-'} />
        <StatusField label="Risque" value={fields.risk ?? '-'} />
      </div>
      <div className="status-grid secondary">
        <StatusField label="Decisions journalisees" value={journal.decisions ?? 0} />
        <StatusField label="Signaux journalises" value={journal.signals ?? 0} />
        <StatusField label="Refus journalises" value={journal.rejections ?? 0} />
      </div>
    </section>
  )
}

function StatusField({ label, value }) {
  return (
    <div className="status-field">
      <span className="status-label">{label}</span>
      <span className="status-value">{String(value)}</span>
    </div>
  )
}

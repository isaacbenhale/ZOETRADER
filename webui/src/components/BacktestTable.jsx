export default function BacktestTable({ report }) {
  const results = report?.results ?? []

  return (
    <section className="panel">
      <h2>Rapport de backtest</h2>
      <p className="hint">
        Mesure historique, pas une garantie. Trie par expectancy. <code>trades</code> faible = mesure peu fiable.
      </p>
      {results.length === 0 ? (
        <p className="hint">Aucun rapport pour l&apos;instant. Lance un backtest.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Instrument</th>
                <th>Strategie</th>
                <th>TF</th>
                <th>Trades</th>
                <th>Win rate</th>
                <th>Expectancy</th>
                <th>Profit factor</th>
                <th>Max DD</th>
                <th>Profitable ?</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={`${result.instrument}-${result.strategy}`}>
                  <td>{result.instrument}</td>
                  <td>{result.strategy}</td>
                  <td>{result.timeframe}</td>
                  <td>{result.trades}</td>
                  <td>{(result.win_rate * 100).toFixed(1)}%</td>
                  <td>{result.expectancy.toFixed(3)}</td>
                  <td>{Number.isFinite(result.profit_factor) ? result.profit_factor.toFixed(2) : '∞'}</td>
                  <td>{result.max_drawdown.toFixed(2)}</td>
                  <td className={result.profitable ? 'profitable-yes' : 'profitable-no'}>
                    {result.profitable ? 'oui' : 'non'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {report?.skipped?.length > 0 && (
        <div className="skipped">
          <strong>Ignore :</strong>
          <ul>
            {report.skipped.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

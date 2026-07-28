export default function ReportView({ report }) {
  const { dataset_summary, warnings, top_correlations, simulation, validation } = report

  return (
    <div className="report">
      <section className="report__summary">
        <div className="report__stat">
          <span className="report__stat-value mono">{dataset_summary.n_rows}</span>
          <span className="report__stat-label">lignes</span>
        </div>
        <div className="report__stat">
          <span className="report__stat-value mono">{dataset_summary.n_columns}</span>
          <span className="report__stat-label">colonnes</span>
        </div>
        <div className="report__stat">
          <span className="report__stat-value mono">{validation.duplicates_count}</span>
          <span className="report__stat-label">doublon(s)</span>
        </div>
      </section>

      {warnings?.length > 0 && (
        <section className="report__warnings">
          {warnings.map((w, i) => (
            <p key={i} className="report__warning">⚠ {w}</p>
          ))}
        </section>
      )}

      {top_correlations?.length > 0 && (
        <section className="report__block">
          <h3 className="report__block-title">Corrélations principales</h3>
          <div className="corr-list">
            {top_correlations.map((c, i) => (
              <div className="corr-row" key={i}>
                <span className="corr-row__pair">
                  {c.column_a} <span className="corr-row__arrow">↔</span> {c.column_b}
                </span>
                <div className="corr-row__bar-track">
                  <div
                    className={`corr-row__bar ${c.value >= 0 ? 'is-positive' : 'is-negative'}`}
                    style={{ width: `${Math.abs(c.value) * 100}%` }}
                  />
                </div>
                <span className="corr-row__value mono">{c.value.toFixed(2)}</span>
              </div>
            ))}
          </div>
          <p className="report__disclaimer">Corrélation n'implique pas causalité.</p>
        </section>
      )}

      {simulation && (
        <section className="report__block">
          <h3 className="report__block-title">Simulation — {simulation.feature}</h3>
          <div className="sim-result">
            <div className="sim-result__value">
              <span className="mono">{simulation.baseline.toFixed(2)}</span>
              <span className="sim-result__label">actuel</span>
            </div>
            <span className="sim-result__sep">→</span>
            <div className="sim-result__value">
              <span className="mono">{simulation.simulated.toFixed(2)}</span>
              <span className="sim-result__label">simulé</span>
            </div>
            {simulation.change_pct_reliable !== false && simulation.change_pct !== null ? (
              <span className={`sim-result__change mono ${simulation.change_pct >= 0 ? 'is-positive' : 'is-negative'}`}>
                {simulation.change_pct >= 0 ? '+' : ''}{simulation.change_pct.toFixed(1)}%
              </span>
            ) : (
              <span className="sim-result__change mono is-unreliable">% non fiable</span>
            )}
          </div>
          {simulation.change_pct_reliable === false && (
            <p className="report__disclaimer">
              Variation en % non fiable ici (valeur de référence trop proche de zéro) —
              se fier aux valeurs absolues ci-dessus.
            </p>
          )}
          <p className="report__disclaimer">
            R² = {simulation.model_r_squared.toFixed(2)} — régression linéaire, échantillon limité.
          </p>
        </section>
      )}
    </div>
  )
}

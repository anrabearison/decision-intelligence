export default function ReportView({ report }) {
  const { dataset_summary, warnings, top_correlations, simulation, validation } = report
  const hasProbabilityPointChange = simulation?.change_percentage_points !== undefined && simulation?.change_percentage_points !== null
  const formatSimulationValue = (value) => (
    hasProbabilityPointChange ? `${(value * 100).toFixed(1)}%` : value.toFixed(2)
  )

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
            {top_correlations.map((c, i) => {
              const isSignificant = c.significant_after_correction !== false
              return (
                <div className={`corr-row ${isSignificant ? '' : 'is-not-significant'}`} key={i}>
                  <span className="corr-row__pair">
                    {c.column_a} <span className="corr-row__arrow">↔</span> {c.column_b}
                    {!isSignificant && (
                      <span className="corr-row__flag mono" title="Peut être due au hasard (comparaisons multiples)">
                        non significatif
                      </span>
                    )}
                  </span>
                  <div className="corr-row__bar-track">
                    <div
                      className={`corr-row__bar ${c.value >= 0 ? 'is-positive' : 'is-negative'}`}
                      style={{ width: `${Math.abs(c.value) * 100}%` }}
                    />
                  </div>
                  <span className="corr-row__value mono">{c.value.toFixed(2)}</span>
                </div>
              )
            })}
          </div>
          <p className="report__disclaimer">
            Corrélation n'implique pas causalité. « Non significatif » : sur le nombre de
            paires testées, cette relation peut apparaître forte par pur hasard
            (correction statistique appliquée : Benjamini-Hochberg).
          </p>
        </section>
      )}

      {simulation && (
        <section className="report__block">
          <h3 className="report__block-title">Simulation — {simulation.feature}</h3>
          <div className="sim-result">
            <div className="sim-result__value">
              <span className="mono">{formatSimulationValue(simulation.baseline)}</span>
              <span className="sim-result__label">actuel</span>
            </div>
            <span className="sim-result__sep">→</span>
            <div className="sim-result__value">
              <span className="mono">{formatSimulationValue(simulation.simulated)}</span>
              <span className="sim-result__label">simulé</span>
            </div>
            {hasProbabilityPointChange ? (
              <span className={`sim-result__change mono ${simulation.change_percentage_points >= 0 ? 'is-positive' : 'is-negative'}`}>
                {simulation.change_percentage_points >= 0 ? '+' : ''}{simulation.change_percentage_points.toFixed(1)} pts
              </span>
            ) : simulation.change_pct_reliable !== false && simulation.change_pct !== null ? (
              <span className={`sim-result__change mono ${simulation.change_pct >= 0 ? 'is-positive' : 'is-negative'}`}>
                {simulation.change_pct >= 0 ? '+' : ''}{simulation.change_pct.toFixed(1)}%
              </span>
            ) : (
              <span className="sim-result__change mono is-unreliable">% non fiable</span>
            )}
          </div>
          {simulation.change_pct_reliable === false && !hasProbabilityPointChange && (
            <p className="report__disclaimer">
              Variation en % non fiable ici (valeur de référence trop proche de zéro) —
              se fier aux valeurs absolues ci-dessus.
            </p>
          )}
          <p className="report__disclaimer">
            R² = {simulation.model_r_squared.toFixed(2)} — {simulation.model_type === 'logistic' ? 'régression logistique' : 'régression linéaire'}, échantillon limité.
          </p>
        </section>
      )}
    </div>
  )
}

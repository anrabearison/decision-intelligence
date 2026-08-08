/**
 * ReportView — affichage du rapport decision-core
 * Bonne pratique React : composant pur, props déstructurées, sous-composants, pas de side-effect
 */
function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—"
  return Number(value).toFixed(decimals)
}

function SeverityBadge({ severity }) {
  const map = { high: "is-high", medium: "is-medium", low: "is-low" }
  return <span className={`badge ${map[severity] || ""}`}>{severity}</span>
}

function MainInsight({ text }) {
  if (!text) return null
  return (
    <section className="report__insight" role="status" aria-live="polite">
      <h3 className="report__block-title">Conclusion principale</h3>
      <p className="report__insight-text">💡 {text}</p>
    </section>
  )
}

function ExploitabilityBadge({ exploitability }) {
  if (!exploitability) return null
  const levelClass = `is-${exploitability.level}`
  return (
    <div className={`exploitability ${levelClass}`}>
      <span className="exploitability__level mono">{exploitability.level.toUpperCase()}</span>
      <span className="exploitability__score mono">{exploitability.score}/100</span>
      <span className="exploitability__summary">{exploitability.summary}</span>
    </div>
  )
}

function SimulationBlock({ simulation }) {
  if (!simulation) return null
  const hasProbabilityPointChange =
    simulation.change_percentage_points !== undefined &&
    simulation.change_percentage_points !== null

  const formatSimulationValue = (value) =>
    hasProbabilityPointChange ? `${(value * 100).toFixed(1)}%` : formatNumber(value, 1)

  const isNonActionable = simulation.actionable === false
  const interval = simulation.prediction_interval
  const cv = simulation.cross_validation

  return (
    <section className="report__block" aria-labelledby="sim-title">
      <h3 id="sim-title" className="report__block-title">
        Simulation — {simulation.feature} → {simulation.target}
        {isNonActionable && <span className="badge is-high">Non actionnable</span>}
      </h3>

      <div className="sim-result">
        <div className="sim-result__value">
          <span className="mono">{formatSimulationValue(simulation.baseline)}</span>
          <span className="sim-result__label">actuel</span>
        </div>
        <span className="sim-result__sep" aria-hidden>
          →
        </span>
        <div className="sim-result__value">
          <span className="mono">{formatSimulationValue(simulation.simulated)}</span>
          <span className="sim-result__label">simulé</span>
        </div>

        {hasProbabilityPointChange ? (
          <span
            className={`sim-result__change mono ${simulation.change_percentage_points >= 0 ? "is-positive" : "is-negative"}`}
          >
            {simulation.change_percentage_points >= 0 ? "+" : ""}
            {formatNumber(simulation.change_percentage_points, 1)} pts
          </span>
        ) : simulation.change_pct_reliable !== false && simulation.change_pct !== null ? (
          <span
            className={`sim-result__change mono ${simulation.change_pct >= 0 ? "is-positive" : "is-negative"}`}
          >
            {simulation.change_pct >= 0 ? "+" : ""}
            {formatNumber(simulation.change_pct, 1)}%
          </span>
        ) : (
          <span className="sim-result__change mono is-unreliable">% non fiable</span>
        )}
      </div>

      {isNonActionable && simulation.non_actionable_reason && (
        <p className="report__warning is-high" role="alert">
          ⚠ {simulation.non_actionable_reason} — Calcul indicatif uniquement.
        </p>
      )}

      {interval && (
        <p className="report__disclaimer">
          Intervalle 80% : [{formatNumber(interval.lower, 1)} → {formatNumber(interval.upper, 1)}] (confiance {Math.round(interval.confidence * 100)}%)
        </p>
      )}

      {cv && (
        <p className="report__disclaimer">
          Validation croisée 5-fold : R² moyen {formatNumber(cv.cv_r2_mean, 2)} — MAE {formatNumber(cv.mae, 1)}, RMSE {formatNumber(cv.rmse, 1)}
        </p>
      )}

      {simulation.change_pct_reliable === false && !hasProbabilityPointChange && (
        <p className="report__disclaimer">
          Variation en % non fiable ici (valeur de référence trop proche de zéro) — se fier aux valeurs absolues.
        </p>
      )}

      <p className="report__disclaimer">
        R² = {formatNumber(simulation.model_r_squared, 2)} —{" "}
        {simulation.model_type === "logistic" ? "régression logistique" : "régression linéaire"}
        {simulation.warnings_structured && ` — ${simulation.warnings_structured.length} alerte(s) structurée(s)`}
      </p>

      {simulation.bounds_applied && (
        <p className="report__disclaimer is-warning">Résultat borné par les limites physiques configurées.</p>
      )}
    </section>
  )
}

export default function ReportView({ report }) {
  if (!report) return null
  const { dataset_summary, warnings, warnings_structured, top_correlations, simulation, validation, exploitability, main_insight } =
    report

  // Préfère warnings_structured si présent, sinon fallback warnings string
  const hasStructured = Array.isArray(warnings_structured) && warnings_structured.length > 0

  return (
    <div className="report">
      <MainInsight text={main_insight} />

      <section className="report__summary" aria-label="Résumé dataset">
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
        <ExploitabilityBadge exploitability={exploitability} />
      </section>

      {hasStructured ? (
        <section className="report__warnings" aria-label="Alertes structurées">
          {warnings_structured.map((w, i) => (
            <div key={i} className={`report__warning is-${w.severity}`}>
              <SeverityBadge severity={w.severity} />
              <span className="report__warning-code mono">{w.code}</span> — {w.message}
              {w.recommendation && <p className="report__warning-reco">→ {w.recommendation}</p>}
            </div>
          ))}
          {/* Conserve les warnings string non structurés en complément */}
          {warnings
            .filter((ws) => !warnings_structured.some((st) => ws.includes(st.message.slice(0, 30))))
            .map((w, i) => (
              <p key={`s-${i}`} className="report__warning">
                ⚠ {w}
              </p>
            ))}
        </section>
      ) : (
        warnings?.length > 0 && (
          <section className="report__warnings" aria-label="Alertes">
            {warnings.map((w, i) => (
              <p key={i} className="report__warning">
                ⚠ {w}
              </p>
            ))}
          </section>
        )
      )}

      {top_correlations?.length > 0 && (
        <section className="report__block">
          <h3 className="report__block-title">Corrélations principales</h3>
          <div className="corr-list">
            {top_correlations.map((c, i) => {
              const isSignificant = c.significant_after_correction !== false
              return (
                <div className={`corr-row ${isSignificant ? "" : "is-not-significant"}`} key={i}>
                  <span className="corr-row__pair">
                    {c.column_a} <span className="corr-row__arrow">↔</span> {c.column_b}
                    {!isSignificant && (
                      <span className="corr-row__flag mono" title="Peut être due au hasard (comparaisons multiples)">
                        non significatif
                      </span>
                    )}
                  </span>
                  <div className="corr-row__bar-track" aria-hidden>
                    <div
                      className={`corr-row__bar ${c.value >= 0 ? "is-positive" : "is-negative"}`}
                      style={{ width: `${Math.abs(c.value) * 100}%` }}
                    />
                  </div>
                  <span className="corr-row__value mono">{formatNumber(c.value, 2)}</span>
                </div>
              )
            })}
          </div>
          <p className="report__disclaimer">
            Corrélation n'implique pas causalité. « Non significatif » : sur le nombre de paires testées, cette relation peut
            apparaître forte par pur hasard (correction Benjamini-Hochberg).
          </p>
        </section>
      )}

      <SimulationBlock simulation={simulation} />
    </div>
  )
}

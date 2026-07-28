"""
Module de rapport - Phase 1a.
Assemble validation + profiling + (optionnel) simulation en une
synthèse structurée, puis la rend en texte ou en HTML.

Règle de conception (voir README) : ne jamais présenter comme
"insight principal" une corrélation triviale sans le nuancer -
chaque corrélation forte affichée rappelle explicitement que
corrélation n'est pas causalité.
"""
import html
import itertools
import pandas as pd

from decision_core.validation import validate_dataset
from decision_core.profiling import descriptive_stats, correlation_matrix, legitimate_numeric_columns
from decision_core.anomaly_detection import detect_anomalies_iqr, MIN_RELIABLE_SAMPLE_SIZE
from decision_core.simulation import simulate_scenario
from decision_core.influence_detection import detect_influential_points
from decision_core.regression import _validate_regression_inputs

SMALL_SAMPLE_THRESHOLD = MIN_RELIABLE_SAMPLE_SIZE


LOW_R_SQUARED_THRESHOLD = 0.3


def generate_report(df: pd.DataFrame, simulation_config: dict | None = None) -> dict:
    warnings = []
    n_rows = len(df)

    if n_rows < SMALL_SAMPLE_THRESHOLD:
        warnings.append(
            f"Échantillon petit ({n_rows} lignes) : les résultats statistiques "
            f"(corrélations, détection d'anomalies, régression) sont indicatifs, "
            f"pas robustes. Recommandé : {SMALL_SAMPLE_THRESHOLD}+ lignes."
        )

    validation = validate_dataset(df)

    numeric_cols = legitimate_numeric_columns(df)
    profiling = {col: descriptive_stats(df[col]) for col in numeric_cols}

    corr = correlation_matrix(df)
    top_correlations = _extract_top_correlations(corr)

    report = {
        "dataset_summary": {
            "n_rows": n_rows,
            "n_columns": len(df.columns),
            "numeric_columns": numeric_cols,
        },
        "validation": validation,
        "profiling": profiling,
        "top_correlations": top_correlations,
        "warnings": warnings,
    }

    if simulation_config is not None:
        simulation = simulate_scenario(
            df,
            target=simulation_config["target"],
            feature=simulation_config["feature"],
            change_pct=simulation_config["change_pct"],
        )
        report["simulation"] = simulation

        # L'avertissement "échantillon petit" plus haut porte sur la taille
        # globale du dataset - insuffisant si les colonnes utilisées par
        # CETTE simulation ont beaucoup de valeurs manquantes (un dataset
        # de 40 lignes peut n'avoir que 5 valeurs valides sur X et Y).
        effective_sample = _validate_regression_inputs(
            df, [simulation_config["feature"], simulation_config["target"]]
        )
        effective_n = len(effective_sample)
        if effective_n < n_rows and effective_n < SMALL_SAMPLE_THRESHOLD:
            warnings.append(
                f"Échantillon effectif réduit pour cette simulation : "
                f"seulement {effective_n} lignes valides sur "
                f"'{simulation_config['feature']}' et "
                f"'{simulation_config['target']}' (sur {n_rows} au total), "
                f"après retrait des valeurs manquantes - résultats "
                f"indicatifs, pas robustes."
            )

        if simulation["model_r_squared"] < LOW_R_SQUARED_THRESHOLD:
            warnings.append(
                f"R² faible ({simulation['model_r_squared']:.2f}) pour la "
                f"simulation sur '{simulation['feature']}' : le modèle "
                f"explique moins de {int(LOW_R_SQUARED_THRESHOLD*100)}% de "
                f"la variance de '{simulation['target']}' - la projection "
                f"est peu fiable, à interpréter avec beaucoup de prudence."
            )

        influence = detect_influential_points(
            df, feature=simulation_config["feature"], target=simulation_config["target"]
        )
        if influence["indices"]:
            warnings.append(
                f"Point(s) influent(s) détecté(s) (ligne(s) "
                f"{influence['indices']}) : ce résultat dépend fortement "
                f"d'un ou plusieurs points spécifiques - une corrélation "
                f"ou une régression peut être largement déformée par un "
                f"seul point atypique, même s'il n'est pas détecté comme "
                f"anomalie sur une seule colonne. Vérifier ces valeurs "
                f"avant de s'y fier."
            )

    return report


def _extract_top_correlations(corr: pd.DataFrame, top_n: int = 5) -> list:
    pairs = []
    seen = set()
    for col_a, col_b in itertools.combinations(corr.columns, 2):
        pair_key = frozenset([col_a, col_b])
        if pair_key in seen:
            continue
        seen.add(pair_key)
        value = corr.loc[col_a, col_b]
        if pd.isna(value):
            continue
        pairs.append({"column_a": col_a, "column_b": col_b, "value": float(value)})

    pairs.sort(key=lambda p: abs(p["value"]), reverse=True)
    return pairs[:top_n]


def render_text_summary(report: dict) -> str:
    lines = []
    ds = report["dataset_summary"]
    lines.append(f"📊 Résumé du dataset : {ds['n_rows']} lignes, {ds['n_columns']} colonnes.")

    if report["validation"]["duplicates_count"] > 0:
        lines.append(f"⚠️ {report['validation']['duplicates_count']} doublon(s) détecté(s).")

    if report["top_correlations"]:
        top = report["top_correlations"][0]
        lines.append(
            f"🔎 Corrélation la plus forte : {top['column_a']} ↔ {top['column_b']} "
            f"({top['value']:.2f}). Rappel : corrélation n'implique pas causalité."
        )

    if "simulation" in report:
        sim = report["simulation"]
        if sim.get("change_pct_reliable", True):
            lines.append(
                f"💡 Simulation sur '{sim['feature']}' : "
                f"{sim['baseline']:.1f} → {sim['simulated']:.1f} "
                f"({sim['change_pct']:+.1f}%)."
            )
        else:
            lines.append(
                f"💡 Simulation sur '{sim['feature']}' : "
                f"{sim['baseline']:.2f} → {sim['simulated']:.2f}. "
                f"Variation en % non fiable ici (valeur de référence trop "
                f"proche de zéro) - se fier aux valeurs absolues plutôt "
                f"qu'au pourcentage."
            )

    for w in report["warnings"]:
        lines.append(f"⚠️ {w}")

    return "\n".join(lines)


def render_html(report: dict) -> str:
    ds = report["dataset_summary"]
    # Échappement systématique de toute donnée dérivée du fichier importé
    # (noms de colonnes notamment) - ces valeurs viennent d'un upload
    # utilisateur non fiable et ne doivent jamais être injectées telles
    # quelles dans du HTML (risque XSS, cf. commit). Le JSON retourné par
    # l'API n'est lui jamais échappé : c'est React qui échappe déjà côté
    # frontend, échapper ici aussi produirait un double échappement.
    text_summary = html.escape(render_text_summary(report)).replace("\n", "<br>")

    correlations_rows = "".join(
        f"<tr><td>{html.escape(str(c['column_a']))}</td>"
        f"<td>{html.escape(str(c['column_b']))}</td>"
        f"<td>{c['value']:.3f}</td></tr>"
        for c in report["top_correlations"]
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Rapport Decision Core</title></head>
<body>
<h1>Rapport d'analyse</h1>
<p>{ds['n_rows']} lignes, {ds['n_columns']} colonnes.</p>
<h2>Synthèse</h2>
<p>{text_summary}</p>
<h2>Corrélations principales</h2>
<table border="1">
<tr><th>Variable A</th><th>Variable B</th><th>Corrélation</th></tr>
{correlations_rows}
</table>
</body>
</html>"""

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
import re
import pandas as pd

from decision_core.validation import validate_dataset
from decision_core.profiling import (
    descriptive_stats,
    correlation_pvalues,
    legitimate_numeric_columns,
    MAX_COLUMNS_FOR_CORRELATION,
)
from decision_core.anomaly_detection import detect_anomalies_iqr, MIN_RELIABLE_SAMPLE_SIZE
from decision_core.simulation import simulate_scenario
from decision_core.influence_detection import detect_influential_points
from decision_core.regression import _validate_regression_inputs
from decision_core.derived_columns import detect_derived_relationships
from decision_core.models import SimulationConfig, AnalysisConfig



SMALL_SAMPLE_THRESHOLD = MIN_RELIABLE_SAMPLE_SIZE

LOW_R_SQUARED_THRESHOLD = 0.3

# R8 — Détection de colonnes temporelles pour le warning de saisonnalité.
# Mots-clés cherchés dans les noms de colonnes (insensible à la casse).
_TEMPORAL_KEYWORDS = [
    "date", "semaine", "week", "mois", "month", "saison", "season",
    "trimestre", "quarter", "annee", "year", "jour", "day", "periode",
    "timestamp", "heure", "hour",
]


def _detect_temporal_columns(df: pd.DataFrame) -> list:
    """Retourne la liste des noms de colonnes dont le nom suggère une
    dimension temporelle (date, semaine, saison, etc.).

    La détection se fait par découpage du nom en mots (éparateurs _ - espace
    et split CamelCase) pour éviter les faux positifs sur des mots composés
    contenant un mot-clé temporel en sous-chaîne :
      - 'Bonjour' contient 'jour' mais n'est pas temporel → non détecté ✓
      - 'Budget_Par_Jour' → mots {'budget', 'par', 'jour'} → détecté ✓
      - 'DateVente' (CamelCase) → 'Date_Vente' → {'date', 'vente'} → détecté ✓
    """
    found = []
    temporal_set = set(_TEMPORAL_KEYWORDS)
    for col in df.columns:
        # 1. Split CamelCase : 'DateVente' → 'Date_Vente'
        split_camel = re.sub(r'([a-z])([A-Z])', r'\1_\2', col)
        # 2. Normaliser les séparateurs et découper en mots
        parts = set(
            split_camel.lower()
            .replace("-", "_")
            .replace(" ", "_")
            .split("_")
        )
        # 3. Intersection avec les mots-clés temporels
        if parts & temporal_set:
            found.append(col)
    return found


def _compute_exploitability_score(
    n_rows: int,
    n_warnings: int,
    n_anomaly_cols: int,
    r_squared: float | None,
) -> dict:
    """R9 — Calcule un score synthétique d'exploitabilité du dataset.

    Logique heuristique :
    - Taille de l'échantillon (< 15 : critique, < 30 : faible, >= 30 : ok)
    - Nombre de warnings générés
    - R² de la simulation si disponible
    - Présence de colonnes avec anomalies

    Retourne un dict avec 'level' (green/orange/red) et 'summary' (texte).
    """
    score = 100

    # Pénalité taille
    if n_rows < 15:
        score -= 50
    elif n_rows < SMALL_SAMPLE_THRESHOLD:
        score -= 25

    # Pénalité warnings (chaque warning = -10, plafonné à -30)
    score -= min(n_warnings * 10, 30)

    # Pénalité anomalies détectées
    score -= n_anomaly_cols * 5

    # Pénalité R² faible sur la simulation
    if r_squared is not None:
        if r_squared < 0.1:
            score -= 30
        elif r_squared < LOW_R_SQUARED_THRESHOLD:
            score -= 15

    score = max(0, score)

    if score >= 70:
        level = "green"
        summary = "Dataset exploitable — les résultats sont interprétables avec confiance."
    elif score >= 40:
        level = "orange"
        summary = "Interprétation prudente — plusieurs limites détectées, croiser avec l'expertise métier."
    else:
        level = "red"
        summary = "Données insuffisantes ou trop limitées — les résultats sont indicatifs uniquement."

    return {"level": level, "score": score, "summary": summary}


def generate_report(
    df: pd.DataFrame,
    simulation_config: SimulationConfig | dict | None = None,
    analysis_config: AnalysisConfig | dict | None = None,
) -> dict:
    """Génère le rapport d'analyse complet du DataFrame.

    Args:
        df: DataFrame source (issu de import_file).
        simulation_config: Configuration de simulation typée SimulationConfig
            ou dict équivalent.
        analysis_config: Configuration d'analyse typée AnalysisConfig
            ou dict équivalent.

    Returns:
        Dict structuré.
    """
    # Rétrocompatibilité et application des règles POO de validation statique
    import inspect
    typed_analysis: AnalysisConfig
    if isinstance(analysis_config, AnalysisConfig):
        typed_analysis = analysis_config
    elif isinstance(analysis_config, dict):
        valid_keys = inspect.signature(AnalysisConfig).parameters.keys()
        filtered_analysis = {k: v for k, v in analysis_config.items() if k in valid_keys}
        typed_analysis = AnalysisConfig(**filtered_analysis)
    else:
        typed_analysis = AnalysisConfig()

    typed_simulation: SimulationConfig | None = None
    if isinstance(simulation_config, SimulationConfig):
        typed_simulation = simulation_config
    elif isinstance(simulation_config, dict):
        valid_keys = inspect.signature(SimulationConfig).parameters.keys()
        filtered_simulation = {k: v for k, v in simulation_config.items() if k in valid_keys}
        typed_simulation = SimulationConfig(**filtered_simulation)


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

    if not numeric_cols:
        warnings.append(
            "Aucune colonne numérique exploitable détectée dans ce "
            "fichier : statistiques, corrélations, détection d'anomalies "
            "et simulation ne peuvent pas être calculées. Vérifiez que "
            "vos colonnes numériques sont bien reconnues comme telles "
            "(voir les limites de détection dans la documentation)."
        )

    # Détection d'anomalies (IQR) par colonne numérique
    anomalies = {}
    for col in numeric_cols:
        result = detect_anomalies_iqr(df[col], k=typed_analysis.iqr_k)
        if result.indices and result.reliable:
            anomalies[col] = result.to_dict()
    if anomalies:
        cols_with_anomalies = ", ".join(anomalies.keys())
        total_anomalies = sum(len(a["indices"]) for a in anomalies.values())
        warnings.append(
            f"Anomalie(s) détectée(s) sur {len(anomalies)} colonne(s) "
            f"({cols_with_anomalies}) : {total_anomalies} valeur(s) "
            f"hors de la plage habituelle au total, potentiellement des "
            f"erreurs de saisie ou des cas exceptionnels à vérifier - "
            f"elles peuvent fortement fausser la moyenne et l'écart-type "
            f"affichés."
        )

    corr_pairs = correlation_pvalues(df)

    derived_relationships = detect_derived_relationships(df, numeric_cols)
    if derived_relationships:
        derived_names = sorted({name for pair in derived_relationships for name in pair})
        warnings.append(
            f"Relation calculée détectée entre {', '.join(derived_names)} : "
            f"une de ces colonnes semble dérivée mathématiquement des "
            f"autres (ex: Total = Prix × Quantité). Leur forte "
            f"corrélation n'est donc pas un insight - c'est une "
            f"conséquence directe du calcul, pas une découverte."
        )
        corr_pairs = [
            p for p in corr_pairs
            if frozenset([p["column_a"], p["column_b"]]) not in derived_relationships
        ]

    top_correlations = _extract_top_correlations(corr_pairs)

    if len(numeric_cols) > MAX_COLUMNS_FOR_CORRELATION:
        warnings.append(
            f"Dataset large ({len(numeric_cols)} colonnes numériques) : "
            f"les corrélations ne sont calculées que sur les "
            f"{MAX_COLUMNS_FOR_CORRELATION} premières colonnes pour des "
            f"raisons de performance. Les statistiques descriptives "
            f"(moyenne, écart-type...) couvrent en revanche toutes les "
            f"colonnes."
        )

    n_tested = len(corr_pairs)
    n_significant = sum(1 for p in corr_pairs if p.get("significant_after_correction"))
    if n_tested >= 6 and n_significant < n_tested:
        warnings.append(
            f"Comparaisons multiples : sur {n_tested} paires de variables "
            f"testées, seulement {n_significant} restent statistiquement "
            f"significatives après correction (Benjamini-Hochberg, seuil "
            f"5%). Plus il y a de colonnes, plus une corrélation isolée "
            f"forte peut apparaître par hasard - se fier au champ "
            f"'significant_after_correction' de chaque paire plutôt qu'à "
            f"sa seule valeur."
        )

    report = {
        "dataset_summary": {
            "n_rows": n_rows,
            "n_columns": len(df.columns),
            "numeric_columns": numeric_cols,
        },
        "validation": validation,
        "profiling": profiling,
        "anomalies": anomalies,
        "top_correlations": top_correlations,
        "warnings": warnings,
    }

    if typed_simulation is not None:
        simulation = simulate_scenario(
            df,
            target=typed_simulation.target,
            feature=typed_simulation.feature,
            change_pct=typed_simulation.change_pct,
            baseline_feature_value=typed_simulation.baseline_feature_value,
            bounds=typed_simulation.bounds,
        )
        report["simulation"] = simulation.to_dict()

        # L'avertissement "échantillon petit" plus haut porte sur la taille
        # globale du dataset - insuffisant si les colonnes utilisées par
        # CETTE simulation ont beaucoup de valeurs manquantes (un dataset
        # de 40 lignes peut n'avoir que 5 valeurs valides sur X et Y).
        effective_sample = _validate_regression_inputs(
            df, [typed_simulation.feature, typed_simulation.target]
        )
        effective_n = len(effective_sample)
        if effective_n < n_rows and effective_n < SMALL_SAMPLE_THRESHOLD:
            warnings.append(
                f"Échantillon effectif réduit pour cette simulation : "
                f"seulement {effective_n} lignes valides sur "
                f"'{typed_simulation.feature}' et "
                f"'{typed_simulation.target}' (sur {n_rows} au total), "
                f"après retrait des valeurs manquantes - résultats "
                f"indicatifs, pas robustes."
            )

        if simulation.model_r_squared < LOW_R_SQUARED_THRESHOLD:
            warnings.append(
                f"R² faible ({simulation.model_r_squared:.2f}) pour la "
                f"simulation sur '{typed_simulation.feature}' : le modèle "
                f"explique moins de {int(LOW_R_SQUARED_THRESHOLD*100)}% de "
                f"la variance de '{typed_simulation.target}' - la projection "
                f"est peu fiable, à interpréter avec beaucoup de prudence."
            )

        influence = detect_influential_points(
            df, feature=typed_simulation.feature, target=typed_simulation.target
        )

        if influence["indices"]:
            warnings.append(
                f"Point(s) influent(s) détecté(s) (ligne(s) "
                f"{influence['indices']}) : ce résultat dépend fortement "
                f"d'un ou plusieurs points spécifiques - une corrélation "
                f"ou une régression peut être largement déformée par un "
                f"seul point atypique. Vérifier ces valeurs avant de "
                f"s'y fier."
            )

    # R8 — Warning saisonnalité : si une colonne temporelle est détectée
    # ET qu'il existe des corrélations fortes, alerter sur le risque
    # d'inversion de causalité liée à la saisonnalité.
    # IMPORTANT : R8 doit être exécuté AVANT R9 pour que le warning
    # saisonnalité soit pris en compte dans le score d'exploitabilité.
    temporal_cols = _detect_temporal_columns(df)
    if temporal_cols:
        strong_corrs = [
            p for p in corr_pairs
            if abs(p["value"]) >= 0.6 and p.get("significant_after_correction")
        ]
        if strong_corrs:
            temporal_names = ", ".join(f"'{c}'" for c in temporal_cols)
            warnings.append(
                f"Dimension temporelle détectée ({temporal_names}) : "
                f"les corrélations fortes observées peuvent refléter des "
                f"effets saisonniers plutôt que des relations causales "
                f"directes. Une hausse de prix en été (haute saison) "
                f"apparaît corrélée à la fréquentation, par exemple — "
                f"sans que le prix en soit la cause. Croiser avec une "
                f"analyse par période avant de tirer des conclusions."
            )

    # R9 — Score d'exploitabilité synthétique.
    # Calculé après R8 pour que le warning saisonnalité soit inclus
    # dans le décompte n_warnings utilisé par le score.
    sim_r_squared = report.get("simulation", {}).get("model_r_squared")
    exploitability = _compute_exploitability_score(
        n_rows=n_rows,
        n_warnings=len(warnings),
        n_anomaly_cols=len(anomalies),
        r_squared=sim_r_squared,
    )
    report["exploitability"] = exploitability

    return report


def _extract_top_correlations(pairs: list, top_n: int = 5) -> list:
    sorted_pairs = sorted(pairs, key=lambda p: abs(p["value"]), reverse=True)
    return sorted_pairs[:top_n]


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

"""
Calcul du score d'exploitabilité pour decision-core.
"""
import pandas as pd
from decision_core.models import ExploitabilityScore


SMALL_SAMPLE_THRESHOLD = 30
LOW_R_SQUARED_THRESHOLD = 0.3


def _warnings_penalty(n_warnings: int) -> int:
    """Calibre la pénalité de warnings en paliers non linéaires.

    Le calibrage vise à refléter correctement les 18 exemples du dossier
    `examples/`, sans rendre chaque warning trop punitif. Les warnings sont
    informatifs, pas tous critiques : un dataset avec 16 warnings doit être
    nettement pénalisé, mais pas tomber automatiquement à 0.
    """
    if n_warnings <= 3:
        return 0
    if n_warnings <= 5:
        return 10
    if n_warnings <= 8:
        return 25
    if n_warnings <= 12:
        return 40
    return 55


def _compute_exploitability_score(
    n_rows: int,
    n_warnings: int,
    n_anomaly_cols: int,
    r_squared: float | None,
) -> ExploitabilityScore:
    """R9 — Calcule un score synthétique d'exploitabilité du dataset.

    Logique heuristique :
    - Taille de l'échantillon (< 15 : critique, < 30 : faible, >= 30 : ok)
    - Nombre de warnings générés
    - R² de la simulation si disponible
    - Présence de colonnes avec anomalies

    Args:
        n_rows: Nombre de lignes du dataset.
        n_warnings: Nombre de warnings générés.
        n_anomaly_cols: Nombre de colonnes avec anomalies.
        r_squared: R² de la simulation si disponible.

    Returns:
        ExploitabilityScore typé avec level, score et summary.
    """
    score = 100

    # Pénalité taille
    if n_rows < 15:
        score -= 50
    elif n_rows < SMALL_SAMPLE_THRESHOLD:
        score -= 25

    # Pénalité warnings calibrée sur les 18 CSV d'examples.
    # Observations empiriques :
    # - 3 warnings sur un dataset de 15 lignes (tourisme) doit rester exploitable
    #   plutôt que tomber au même niveau que un dataset très bruyant.
    # - 4-5 warnings correspondent à des limites modérées, 7-8 à des limites fortes,
    #   10-12 à une qualité nettement dégradée et >12 à une situation critique.
    # Utiliser des paliers plutôt qu'une pénalité linéaire évite de faire chuter
    # un dataset à 0 alors que les warnings restent informatifs.
    score -= _warnings_penalty(n_warnings)

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

    return ExploitabilityScore(level=level, score=score, summary=summary)

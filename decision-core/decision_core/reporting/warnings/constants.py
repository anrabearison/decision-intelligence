"""
Constantes partagées pour les warnings de decision-core.
"""
from decision_core.quality.anomaly_detection import MIN_RELIABLE_SAMPLE_SIZE

SMALL_SAMPLE_THRESHOLD = MIN_RELIABLE_SAMPLE_SIZE
LOW_R_SQUARED_THRESHOLD = 0.3
ASYMMETRY_THRESHOLD = 0.4  # Calibré sur 18 domaines (21% des colonnes au-dessus)
MAX_NONLINEARITY_PAIRS = 300
MAX_NONLINEARITY_WARNINGS = 3

# R8 — Détection de colonnes temporelles pour le warning de saisonnalité.
# Mots-clés cherchés dans les noms de colonnes (insensible à la casse).
_TEMPORAL_KEYWORDS = [
    "date", "semaine", "week", "mois", "month", "saison", "season",
    "trimestre", "quarter", "annee", "year", "jour", "day", "periode",
    "timestamp", "heure", "hour",
]

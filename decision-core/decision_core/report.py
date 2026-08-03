"""
Fichier de compatibilité pour decision_core.report.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.reporting pour préserver la rétrocompatibilité des imports.
"""
from decision_core.reporting import generate_report, render_text_summary, render_html
from decision_core.reporting.warnings import _detect_temporal_columns
from decision_core.reporting.scoring import _compute_exploitability_score

__all__ = [
    "generate_report",
    "render_text_summary",
    "render_html",
    "_detect_temporal_columns",
    "_compute_exploitability_score",
]

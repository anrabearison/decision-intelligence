"""
Package de génération de rapports pour decision-core.

Ce package regroupe les fonctions de construction, de scoring,
de warnings et de rendu pour les rapports d'analyse.
"""
from decision_core.reporting.builder import generate_report
from decision_core.reporting.renderers import render_text_summary, render_html

__all__ = [
    "generate_report",
    "render_text_summary",
    "render_html",
]

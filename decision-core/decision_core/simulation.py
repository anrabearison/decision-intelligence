"""
Fichier de compatibilité pour decision_core.simulation.

Ce fichier réexporte toutes les fonctions depuis le nouveau package
decision_core.simulation pour préserver la rétrocompatibilité des imports.
"""
from decision_core.simulation.scenario import simulate_scenario

__all__ = [
    "simulate_scenario",
]



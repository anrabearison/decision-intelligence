"""
Package de warnings contextuels pour decision-core.

Ce package fournit des fonctions pour détecter différents types de warnings
statistiques et contextuels à inclure dans les rapports d'analyse.
"""
from .seasonality import _build_seasonality_warnings, _detect_temporal_columns
from .correlation import _build_correlation_warnings
from .simulation import _build_simulation_warnings
from .nonlinearity import _build_nonlinearity_warnings
from .asymmetry import _build_asymmetry_warnings

__all__ = [
    "_build_seasonality_warnings",
    "_detect_temporal_columns",
    "_build_correlation_warnings",
    "_build_simulation_warnings",
    "_build_nonlinearity_warnings",
    "_build_asymmetry_warnings",
]

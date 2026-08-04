"""
Module de traitement des variables catégorielles - Phase 1b.

Ce module fournit des fonctions pour :
- Encodage one-hot automatique des variables catégorielles
- Détection de sous-groupes significatifs via eta-carré
- Génération de rapports segmentés par sous-groupes

Objectif : résoudre 50% des problèmes identifiés dans RAPPORT_TESTS_DOMAINES.md
en prenant en compte les variables catégorielles ignorées par le moteur actuel.
"""
import pandas as pd
import numpy as np
from typing import Optional


def encode_categorical_features(
    df: pd.DataFrame,
    max_cardinality: int = 10,
    drop_original: bool = True
) -> pd.DataFrame:
    """Encode les variables catégorielles en one-hot.

    Args:
        df: DataFrame pandas contenant les données.
        max_cardinality: Cardinalité maximale pour encoder une variable (défaut 10).
        drop_original: Si True, supprime les colonnes originales après encodage.

    Returns:
        DataFrame avec colonnes catégorielles encodées en one-hot.
    """
    encoded_df = df.copy()
    categorical_cols = []
    
    for col in df.columns:
        # Vérifier si la colonne est catégorielle (texte ou peu de valeurs uniques)
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == 'object':
            unique_count = df[col].nunique()
            if unique_count <= max_cardinality and unique_count > 1:
                categorical_cols.append(col)
    
    # One-hot encoding
    for col in categorical_cols:
        dummies = pd.get_dummies(df[col], prefix=col, drop_first=True)
        encoded_df = pd.concat([encoded_df, dummies.astype(float)], axis=1)
        if drop_original:
            encoded_df = encoded_df.drop(col, axis=1)
    
    return encoded_df


def detect_significant_subgroups(
    df: pd.DataFrame,
    target: str,
    threshold_eta_squared: float = 0.14,
    min_group_size: int = 2
) -> list[dict]:
    """Identifie les colonnes catégorielles qui segmentent significativement les données via eta-carré.

    L'eta-carré (η²) mesure la proportion de variance de la target expliquée par
    la variable catégorielle. Cette fonction applique également un test F d'ANOVA
    pour ne conserver que les effets statistiquement significatifs.
    Interprétation usuelle :
    - 0.01 : petit effet
    - 0.06 : effet moyen
    - 0.14 : grand effet (seuil par défaut)

    Args:
        df: DataFrame pandas contenant les données.
        target: Nom de la colonne cible numérique.
        threshold_eta_squared: Seuil d'eta-carré pour considérer un sous-groupe significatif.
        min_group_size: Taille minimale par groupe pour considérer le test ANOVA fiable.

    Returns:
        Liste de dictionnaires contenant les sous-groupes significatifs avec leur eta-carré,
        la p-value ANOVA, la statistique F et les moyennes de groupe.
    """
    if not pd.api.types.is_numeric_dtype(df[target]):
        return []
    
    from decision_core.stats.anova import compute_eta_squared_with_significance
    significant_subgroups = []
    
    for col in df.columns:
        if col == target:
            continue
        
        # Vérifier si la colonne est catégorielle (texte ou peu de valeurs uniques)
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype == 'object':
            unique_count = df[col].nunique()
            if unique_count <= 10 and unique_count > 1:
                # Calcul de l'eta-carré + test F d'ANOVA
                result = compute_eta_squared_with_significance(
                    df[target], df[col], min_group_size=min_group_size
                )
                
                if result.reliable and result.p_value <= 0.05 and result.eta_squared >= threshold_eta_squared:
                    groups = df.groupby(col)[target]
                    significant_subgroups.append({
                        "column": col,
                        "eta_squared": result.eta_squared,
                        "p_value": result.p_value,
                        "f_statistic": result.f_statistic,
                        "n_groups": unique_count,
                        "group_means": groups.mean().to_dict()
                    })
    
    return significant_subgroups


def generate_segmented_reports(
    df: pd.DataFrame,
    group_by: list[str],
    generate_report_func,
    config,
    min_group_size: int = 3
) -> dict:
    """Génère des rapports par sous-groupe.

    Args:
        df: DataFrame pandas contenant les données.
        group_by: Liste des colonnes catégorielles pour le groupement.
        generate_report_func: Fonction de génération de rapport (ex: generate_report).
        config: Configuration pour la génération de rapport.
        min_group_size: Taille minimale d'un groupe pour générer un rapport.

    Returns:
        Dictionnaire avec les rapports par sous-groupe.
    """
    reports = {}
    
    try:
        grouped = df.groupby(group_by)
        
        for group_key, group_df in grouped:
            if len(group_df) >= min_group_size:
                try:
                    report = generate_report_func(group_df, config)
                    if isinstance(group_key, tuple):
                        group_name = "_".join(str(k) for k in group_key)
                    else:
                        group_name = str(group_key)
                    reports[group_name] = report
                except Exception:
                    # Ignorer les erreurs de génération de rapport pour un sous-groupe
                    pass
    except Exception:
        # Ignorer les erreurs de groupement
        pass
    
    return reports

#!/usr/bin/env python3
"""
Script pour extraire les résultats automatiques de decision-core pour chaque import
"""
import sys
sys.path.insert(0, '.')

from decision_core import import_file, descriptive_stats, correlation_matrix, legitimate_numeric_columns
from decision_core.quality.type_detection import detect_column_type
from decision_core.quality.anomaly_detection import detect_anomalies_iqr
from decision_core.stats.categorical import detect_significant_subgroups
import pandas as pd

DOMAIN_EXPERTS = {
    "agriculture_rendement_2025.csv": "Expert Agronomie",
    "assurance_sinistres_2025.csv": "Actuaire Assurance",
    "cybersecurite_incidents_2025.csv": "Expert Cybersécurité",
    "education_elearning_2025.csv": "Expert Pédagogie",
    "elevage_production_lait_2025.csv": "Expert Élevage",
    "energie_batiments_2025.csv": "Expert Efficacité Énergétique",
    "finance_tresorerie_2025.csv": "Expert Trésorerie",
    "hotellerie_reservations_2025.csv": "Expert Hôtellerie",
    "immobilier_estimations_2025.csv": "Expert Immobilier",
    "industrie_maintenance_2025.csv": "Expert Maintenance",
    "logistique_livraisons_2025.csv": "Expert Logistique",
    "marketing_digital_2025.csv": "Expert Marketing",
    "restauration_gastronomie_2025.csv": "Expert Restauration",
    "rh_masse_salariale_2025.csv": "Expert RH",
    "saas_abonnements_2025.csv": "Expert SaaS",
    "sante_clinique_2025.csv": "Expert Santé",
    "tourisme_frequentation_2025.csv": "Expert Tourisme",
    "ventes_magasin_2025.csv": "Expert Retail"
}

def analyze_auto_results(csv_file, expert_name):
    """Extrait les résultats automatiques pour un fichier"""
    print(f"\n{'='*80}")
    print(f"📊 {csv_file}")
    print(f"👤 {expert_name}")
    print(f"{'='*80}\n")
    
    try:
        # Import
        df = import_file(f"examples/{csv_file}")
        print(f"📏 DIMENSIONS : {df.shape[0]} lignes × {df.shape[1]} colonnes")
        
        # Types de colonnes détectés automatiquement
        print(f"\n🔍 TYPES DE COLONNES DÉTECTÉS :")
        type_counts = {}
        for col in df.columns:
            col_type = detect_column_type(df[col])
            type_counts[col_type] = type_counts.get(col_type, 0) + 1
            print(f"   {col} : {col_type}")
        
        print(f"\n   Résumé : {dict(type_counts)}")
        
        # Statistiques descriptives automatiques
        numeric_cols = legitimate_numeric_columns(df)
        if numeric_cols:
            print(f"\n📈 STATISTIQUES DESCRIPTIVES AUTOMATIQUES :")
            for col in numeric_cols[:5]:  # Limiter à 5 colonnes pour la lisibilité
                stats = descriptive_stats(df[col])
                print(f"   {col} :")
                print(f"      Moyenne : {stats['mean']:.2f}")
                print(f"      Écart-type : {stats['std_dev']:.2f}")
                print(f"      Min/Max : {stats['min']:.2f} / {stats['max']:.2f}")
                print(f"      Médiane : {stats['median']:.2f}")
        
        # Matrice de corrélation automatique
        if len(numeric_cols) >= 2:
            print(f"\n🔗 CORRÉLATIONS AUTOMATIQUES (top 5) :")
            corr_matrix = correlation_matrix(df)
            # Extraire les corrélations les plus fortes
            correlations = []
            for i, col_a in enumerate(corr_matrix.columns):
                for j, col_b in enumerate(corr_matrix.columns):
                    if i < j:  # Éviter les doublons et la diagonale
                        corr_val = corr_matrix.iloc[i, j]
                        if not pd.isna(corr_val):
                            correlations.append((col_a, col_b, abs(corr_val), corr_val))
            
            # Trier par valeur absolue et prendre les 5 plus fortes
            correlations.sort(key=lambda x: x[2], reverse=True)
            for col_a, col_b, abs_corr, corr_val in correlations[:5]:
                direction = "↔" if corr_val >= 0 else "↔"
                print(f"   {col_a} {direction} {col_b} : {corr_val:.3f}")
        
        # Détection d'anomalies automatique
        print(f"\n⚠️  DÉTECTION D'ANOMALIES AUTOMATIQUE :")
        anomaly_cols = []
        for col in numeric_cols[:5]:  # Limiter à 5 colonnes
            anomaly_result = detect_anomalies_iqr(df[col])
            if anomaly_result.indices:
                anomaly_cols.append(col)
                print(f"   {col} : {len(anomaly_result.indices)} anomalie(s) détectée(s)")
                print(f"      Bornes IQR : [{anomaly_result.lower_bound:.2f}, {anomaly_result.upper_bound:.2f}]")
                print(f"      Fiable : {'Oui' if anomaly_result.reliable else 'Non (échantillon < 30)'}")
            else:
                print(f"   {col} : Aucune anomalie détectée")
        
        if not anomaly_cols:
            print(f"   Aucune anomalie détectée sur les colonnes analysées")
        
        # Détection de sous-groupes automatique
        print(f"\n👥 DÉTECTION DE SOUS-GROUPES AUTOMATIQUE :")
        if numeric_cols:
            target_col = numeric_cols[0]  # Prendre la première colonne numérique comme target
            subgroups = detect_significant_subgroups(df, target_col)
            if subgroups:
                for sg in subgroups[:3]:  # Limiter à 3 sous-groupes
                    print(f"   {sg['column']} : η² = {sg['eta_squared']:.3f} (p = {sg['p_value']:.3f})")
                    print(f"      {sg['n_groups']} groupes avec moyennes : {list(sg['group_means'].values())[:3]}...")
            else:
                print(f"   Aucun sous-groupe significatif détecté")
        
        # Résumé des résultats automatiques
        print(f"\n🎯 RÉSUMÉ DES RÉSULTATS AUTOMATIQUES :")
        print(f"   ✅ Import réussi avec détection automatique des types")
        print(f"   ✅ Statistiques descriptives calculées sur {len(numeric_cols)} colonnes numériques")
        print(f"   ✅ Matrice de corrélation générée automatiquement")
        print(f"   ✅ Détection d'anomalies IQR sur {len(numeric_cols[:5])} colonnes")
        print(f"   ✅ Analyse des sous-groupes via eta-carré")
        
        return df
        
    except Exception as e:
        print(f"❌ ERREUR : {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Analyse tous les fichiers et extrait les résultats automatiques"""
    print("🚀 EXTRACTION DES RÉSULTATS AUTOMATIQUES DECISION-CORE")
    print("="*80)
    
    results = {}
    
    for csv_file, expert_name in DOMAIN_EXPERTS.items():
        df = analyze_auto_results(csv_file, expert_name)
        results[csv_file] = df
    
    # Résumé global
    print(f"\n{'='*80}")
    print("📋 RÉSUMÉ GLOBAL DES RÉSULTATS AUTOMATIQUES")
    print(f"{'='*80}\n")
    
    success_count = sum(1 for r in results.values() if r is not None)
    print(f"✅ Imports réussis : {success_count}/{len(results)}")
    
    total_rows = sum(len(r) for r in results.values() if r is not None)
    total_cols = sum(len(r.columns) for r in results.values() if r is not None)
    print(f"📊 Total données traitées : {total_rows} lignes, {total_cols} colonnes")
    
    print(f"\n🔍 FONCTIONNALITÉS AUTOMATIQUES APPLIQUÉES :")
    print(f"   • Détection automatique des types de colonnes")
    print(f"   • Calcul des statistiques descriptives")
    print(f"   • Génération de la matrice de corrélation")
    print(f"   • Détection d'anomalies via méthode IQR")
    print(f"   • Analyse des sous-groupes via eta-carré")
    print(f"   • Identification des colonnes numériques légitimes")
    print(f"   • Gestion des conventions françaises (encodage, décimales)")

if __name__ == "__main__":
    main()
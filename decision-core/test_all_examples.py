#!/usr/bin/env python3
"""
Script de test pour tous les fichiers examples - simulation d'analyse par domaine
"""
import sys
sys.path.insert(0, '.')

from decision_core import import_file, generate_report, render_text_summary
from decision_core.models import AnalysisConfig

# Mapping des domaines avec leurs experts simulés
DOMAIN_EXPERTS = {
    "agriculture_rendement_2025.csv": "Expert Agronomie - Analyse des rendements cultures",
    "assurance_sinistres_2025.csv": "Actuaire Assurance - Analyse des sinistres",
    "cybersecurite_incidents_2025.csv": "Expert Cybersécurité - Analyse des incidents",
    "education_elearning_2025.csv": "Expert Pédagogie - Analyse e-learning",
    "elevage_production_lait_2025.csv": "Expert Élevage - Analyse production laitière",
    "energie_batiments_2025.csv": "Expert Efficacité Énergétique - Analyse bâtiments",
    "finance_tresorerie_2025.csv": "Expert Trésorerie - Analyse flux financiers",
    "hotellerie_reservations_2025.csv": "Expert Hôtellerie - Analyse réservations",
    "immobilier_estimations_2025.csv": "Expert Immobilier - Analyse estimations",
    "industrie_maintenance_2025.csv": "Expert Maintenance Industrielle - Analyse pannes",
    "logistique_livraisons_2025.csv": "Expert Logistique - Analyse livraisons",
    "marketing_digital_2025.csv": "Expert Marketing Digital - Analyse campagnes",
    "restauration_gastronomie_2025.csv": "Expert Restauration - Analyse ventes",
    "rh_masse_salariale_2025.csv": "Expert RH - Analyse masse salariale",
    "saas_abonnements_2025.csv": "Expert SaaS - Analyse abonnements",
    "sante_clinique_2025.csv": "Expert Santé - Analyse clinique",
    "tourisme_frequentation_2025.csv": "Expert Tourisme - Analyse fréquentation",
    "ventes_magasin_2025.csv": "Expert Retail - Analyse ventes magasin"
}

def analyze_domain(csv_file, expert_name):
    """Analyse un fichier CSV spécifique avec le contexte de l'expert du domaine"""
    print(f"\n{'='*80}")
    print(f"📊 DOMAINE : {csv_file}")
    print(f"👤 EXPERT : {expert_name}")
    print(f"{'='*80}\n")
    
    try:
        # Import du fichier
        df = import_file(f"examples/{csv_file}")
        print(f"✅ Import réussi : {df.shape[0]} lignes, {df.shape[1]} colonnes")
        print(f"📋 Colonnes : {', '.join(df.columns.tolist())}")
        
        # Génération du rapport
        config = AnalysisConfig(iqr_k=1.5)
        report = generate_report(df, config)
        
        # Affichage du rapport
        print(f"\n{'='*80}")
        print("📈 RAPPORT D'ANALYSE")
        print(f"{'='*80}\n")
        print(render_text_summary(report))
        
        # Score d'exploitabilité
        if hasattr(report, 'exploitability'):
            score = report.exploitability
            print(f"\n🎯 SCORE D'EXPLOITABILITÉ : {score.score}/100 ({score.level})")
            print(f"💬 {score.summary}")
        
        # Warnings détaillés
        if report.warnings:
            print(f"\n⚠️  {len(report.warnings)} AVERTISSEMENT(S) DÉTECTÉ(S) :")
            for i, warning in enumerate(report.warnings, 1):
                print(f"   {i}. {warning}")
        
        return report
        
    except Exception as e:
        print(f"❌ ERREUR lors de l'analyse : {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Analyse tous les fichiers examples"""
    print("🚀 LANCEMENT DE L'ANALYSE TOUS DOMAINES")
    print("="*80)
    
    results = {}
    
    for csv_file, expert_name in DOMAIN_EXPERTS.items():
        report = analyze_domain(csv_file, expert_name)
        results[csv_file] = report
    
    # Résumé global
    print(f"\n{'='*80}")
    print("📋 RÉSUMÉ GLOBAL DES ANALYSES")
    print(f"{'='*80}\n")
    
    success_count = sum(1 for r in results.values() if r is not None)
    print(f"✅ Analyses réussies : {success_count}/{len(results)}")
    
    if success_count > 0:
        scores = [r.exploitability.score for r in results.values() if r is not None]
        avg_score = sum(scores) / len(scores)
        print(f"📊 Score moyen d'exploitabilité : {avg_score:.1f}/100")
        
        green_count = sum(1 for r in results.values() if r is not None and r.exploitability.level == "green")
        orange_count = sum(1 for r in results.values() if r is not None and r.exploitability.level == "orange")
        red_count = sum(1 for r in results.values() if r is not None and r.exploitability.level == "red")
        
        print(f"🟢 Datasets verts (exploitables) : {green_count}")
        print(f"🟠 Datasets oranges (prudence) : {orange_count}")
        print(f"🔴 Datasets rouges (limités) : {red_count}")

if __name__ == "__main__":
    main()